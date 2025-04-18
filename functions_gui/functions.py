import os
import csv
import struct
import shutil
import tifffile
import numpy as np
import xml.etree.ElementTree as ET

# TODO: and the ability to import movies from the lightsheet and FV

def imagej_metadata_tags(metadata, byteorder):
    """Return IJMetadata and IJMetadataByteCounts tags from metadata dict.

    The tags can be passed to the TiffWriter.save function as extratags.

    """
    header = [{'>': b'IJIJ', '<': b'JIJI'}[byteorder]]
    bytecounts = [0]
    body = []

    def writestring(data, byteorder):
        return data.encode('utf-16' + {'>': 'be', '<': 'le'}[byteorder])

    def writedoubles(data, byteorder):
        return struct.pack(byteorder+('d' * len(data)), *data)

    def writebytes(data, byteorder):
        return data.tobytes()

    metadata_types = (
        ('Info', b'info', 1, writestring),
        ('Labels', b'labl', None, writestring),
        ('Ranges', b'rang', 1, writedoubles),
        ('LUTs', b'luts', None, writebytes),
        ('Plot', b'plot', 1, writebytes),
        ('ROI', b'roi ', 1, writebytes),
        ('Overlays', b'over', None, writebytes))

    for key, mtype, count, func in metadata_types:
        if key not in metadata:
            continue
        if byteorder == '<':
            mtype = mtype[::-1]
        values = metadata[key]
        if count is None:
            count = len(values)
        else:
            values = [values]
        header.append(mtype + struct.pack(byteorder+'I', count))
        for value in values:
            data = func(value, byteorder)
            body.append(data)
            bytecounts.append(len(data))

    body = b''.join(body)
    header = b''.join(header)
    data = header + body
    bytecounts[0] = len(header)
    bytecounts = struct.pack(byteorder+('I' * len(bytecounts)), *bytecounts)
    return ((50839, 'B', len(data), data, True),
            (50838, 'I', len(bytecounts)//4, bytecounts, True))

def extract_metadata(xml_file, log_params):
    """
    Extracts metadata from an XML file.

    Parameters:
    - xml_file (str): The path to the XML file.
    - log_params (dict): A dictionary to store any issues encountered during extraction.

    Returns:
    - bit_depth (str): The bit depth value extracted from the XML file.
    - dwell_time (str): The dwell time value extracted from the XML file.
    - helios_nd_filter_values (dict): A dictionary containing the Helios ND Filter values extracted from the XML file.
    - laser_power_values (dict): A dictionary containing the Laser Power values extracted from the XML file.
    - objective_lens_description (str): The objective lens description extracted from the XML file.
    - log_params (dict): The updated log_params dictionary with any issues encountered during extraction.
    """

    # Step 1: Make a copy of the XML file
    backup_file = xml_file + ".backup"
    try:
        shutil.copy(xml_file, backup_file)
    except Exception as e:
        log_params['Issues'] = f"Error creating a backup of the XML file: {str(e)}"
        return None, None, None, None, None, log_params

    # Step 2: Update the version in the backup file
    try:
        with open(backup_file, "r") as file:
            lines = file.readlines()
    
        # Remove the line directly after interlacedScanTrackLasers and interlacedScanTrackPowers elements because they have imcompatible XML syntax
        x=0
        for line in lines:
            if "interlacedScanTrackLasers" in line:
                del lines[x + 1]
            elif "interlacedScanTrackPowers" in line:
                del lines[x + 1]
            x+=1

        # Write the updated lines back to the backup file
        with open(backup_file, "w") as file:
            file.writelines(lines)
    except Exception as e:
        log_params['Issues'] = f"Error updating XML version in backup: {str(e)}"
        return None, log_params
    
    tree = ET.parse(backup_file)
    root = tree.getroot()

    # get the bit depth with key="bitDepth"
    bit_depth_element = root.find("./PVStateShard/PVStateValue[@key='bitDepth']")
    if bit_depth_element is not None:
        bit_depth = bit_depth_element.attrib['value']
    else:
        log_params['Issues'] = "Bit Depth not found in the XML."

    # Find the PVStateValue element with key="dwellTime"
    dwell_time_element = root.find("./PVStateShard/PVStateValue[@key='dwellTime']")
    if dwell_time_element is not None:
        dwell_time = dwell_time_element.attrib['value']
    else:
        log_params['Issues'] = "Dwell time not found in the XML."

    # Find the PVStateValue element with key="heliosNDFilter"
    helios_nd_filter_element = root.find("./PVStateShard/PVStateValue[@key='heliosNDFilter']")
    if helios_nd_filter_element is not None:
        helios_nd_filter_values = {}
        for indexed_value in helios_nd_filter_element.findall("./IndexedValue"):
            index = indexed_value.attrib['index']
            value = indexed_value.attrib['description']
            helios_nd_filter_values[index] = value
    else:
        log_params['Issues'] = "Helios ND Filter values not found in the XML."

    # Find the PVStateValue element with key="laserPower"
    laser_power_element = root.find("./PVStateShard/PVStateValue[@key='laserPower']")
    if laser_power_element is not None:
        laser_power_values = {}
        for indexed_value in laser_power_element.findall("./IndexedValue"):
            index = indexed_value.attrib['index']
            value = indexed_value.attrib['value']
            description = indexed_value.attrib['description']
            laser_power_values[index] = f'value: {value}, description: {description}'
    else:
        log_params['Issues'] = "Laser Power values not found in the XML."

    # Find the PVStateValue element with key="objectiveLens"
    objective_lens_element = root.find("./PVStateShard/PVStateValue[@key='objectiveLens']")
    if objective_lens_element is not None:
        objective_lens_description = objective_lens_element.attrib['value']
    else:
        log_params['Issues'] = "Objective Lens description not found in the XML."

    # Find the frame rate
    frames = root.findall('.//Frame')
    absolute_times = {}
    for index, frame in enumerate(frames, start=1):
        absolute_time = frame.attrib.get('absoluteTime')
        files = frame.findall('File')
        for file in files:
            filename = file.attrib.get('filename')
            if "000001.ome.tif" in filename:
                name = int(filename.split("_")[-3].split("e")[-1])
                absolute_times[name] = absolute_time
    num_frames = len(absolute_times)
    total_time = float(absolute_times[num_frames])
    framerate = total_time / num_frames

    # Find the microns per pixel values
    microns_per_pixel_element = root.find(".//PVStateValue[@key='micronsPerPixel']")
    microns_per_pixel = {}
    for indexed_value in microns_per_pixel_element.findall("./IndexedValue"):
        axis = indexed_value.attrib["index"]
        value = float(indexed_value.attrib["value"])
        microns_per_pixel[axis] = value 

    # Step 4: Delete the backup file
    try:
        os.remove(backup_file)
    except Exception as e:
        log_params['Issues'] = f"Error deleting backup file: {str(e)}"

    return bit_depth, dwell_time, helios_nd_filter_values, laser_power_values, objective_lens_description, log_params, framerate, microns_per_pixel['XAxis'], microns_per_pixel['YAxis'], microns_per_pixel['ZAxis']

def make_log(
    logPath: str, 
    logParams: dict
):
    '''
    Creates a log file in the specified directory with the specified parameters.

    Parameters
    directory : str
        The directory in which to create the log file.
    logParams : dict
        A dictionary containing the parameters to be logged.
    '''
    logFile = open(logPath, "w")                                    
    for key, value in logParams.items():                            
        logFile.write('%s: %s\n' % (key, value))                    
    logFile.close()   

def create_hyperstack(folder_path, avg_project=False, max_project=False, single_plane=False):
    '''
    Create a hyperstack from the tiff files in the specified folder.

    Parameters:
    folder_path : str
        The folder containing the tiff files to be combined into a hyperstack.
    max_project : bool
        Whether or not to create a maximum projection of the hyperstack.

    Returns:
    numpy.ndarray
        The hyperstack created from the tiff files in the specified folder.
    '''
    # Start without image type
    image_type = None

    # Get all the tif files in the folder
    folder_tif_files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.endswith('.tif')]

    if single_plane == True:
        image_type = "single_plane"

    else:
        # If last tif file is 'Cycle00001', then just a single frame
        last_file_name = folder_tif_files[-1]
        single_timepoint = True if last_file_name.split('_')[-3] == 'Cycle00001' else False

        # Collect all files in the folder for specific image types
        if single_timepoint:
            if max_project:
                image_type = "multi_plane_single_timepoint_max_project"
            elif avg_project:
                image_type = "multi_plane_single_timepoint_avg_project"
            else:
                image_type = "multi_plane_single_timepoint"
                
        else:
            if max_project:
                image_type = "multi_plane_multi_timepoint_max_project"
            elif avg_project:
                image_type = "multi_plane_multi_timepoint_avg_project"
            else:
                image_type = "multi_plane_multi_timepoint"

    # Sort files to ensure correct order
    folder_tif_files.sort()

    # Collect the files corresponding to each channel and put in dict
    channel_files = {}
    for file in folder_tif_files:
        channel_name = os.path.basename(file).split('_')[-2] 
        if channel_name not in channel_files:
            channel_files[channel_name] = []
        channel_files[channel_name].append(file)

    # Read/create images for each channel
    channel_images = {}
    for channel_name, files in channel_files.items():
        try:
            channel_images[channel_name] = [tifffile.imread(file, is_ome=False) for file in files]
        except Exception as e:
            print(f"Error reading TIFF file for channel {channel_name}: {e}")
            return None, None

    # Stack the images for each channel
    stacked_images = {channel_name: np.stack(images) for channel_name, images in channel_images.items()}

    # Stack images across channels
    merged_images = np.stack(list(stacked_images.values()), axis=1)

    # Adjust axes based on image type, max projected images do not need to be adjusted
    if image_type == "multi_plane_multi_timepoint" or image_type == "multi_plane_single_timepoint":
        merged_images = np.moveaxis(merged_images, [0, 1, 2, 3, 4], [0, 2, 1, 3, 4])        
    if image_type == "single_plane" and len(merged_images.shape) == 5:
        merged_images = np.moveaxis(merged_images, [0, 1, 2, 3, 4], [1, 2, 0, 3, 4])
    elif image_type == "single_plane" and len(merged_images.shape) == 4:
        image_type = "single_plane_single_frame"

    print(f"Image type: {image_type}")
    print(f"Image shape: {merged_images.shape}")

    # If the user would like a max projected image, max project
    if max_project == True and image_type != "single_plane" and image_type != "single_plane_single_frame":
        merged_images = np.max(merged_images, axis = 2)
    if avg_project == True and image_type != "single_plane" and image_type != "single_plane_single_frame":
        merged_images = np.mean(merged_images, axis = 2)
    

    return merged_images, image_type

def determine_scope(
    folder_path: str
):
    if '.oif' in folder_path:
        return 'Olympus'
    else:
        return 'Bruker'
    
def create_hyperstack_olympus(
    image_path: str
):
    if image_path.endswith(".oif"):
        image = tifffile.imread(image_path, is_ome=True)
        return image

def process_folder(folder_name, 
                   parent_folder_path, 
                   processed_images_path, 
                   imagej_tags, 
                   avg_projection,
                   max_projection, 
                   log_details, 
                   metadata_csv_path,
                   single_plane=False
                   ) -> dict:
    '''
    Process the folder and create the hyperstack. Also extract metadata and write to CSV.
    '''
    # Check for XML file and get relevant metadata
    folder_path = os.path.join(parent_folder_path, folder_name)
    xml_files = [file for file in os.listdir(folder_path) if os.path.splitext(file)[1] == ".xml"]   
    if not xml_files:
        raise FileNotFoundError(f"No XML file found in folder {folder_name}")
    else:
        xml_file_path = os.path.join(folder_path, xml_files[0])
        bit_depth, dwell_time, helios_nd_filter_values, laser_power_values, objective_lens_description, log_details, frame_rate, X_microns_per_pixel, Y_microns_per_pixel, Z_microns_per_pixel = extract_metadata(xml_file_path, log_details)

    # Create the hyperstack and get the image type
    hyperstack, image_type = create_hyperstack(folder_path, avg_projection, max_projection, single_plane)

    # Recalculate the frame rate for single plane: divide by number of frames
    frame_rate = frame_rate / hyperstack.shape[0] if image_type == 'single_plane' else frame_rate
    
    # create the output image name
    image_output_name = os.path.join(processed_images_path, f"{'MAX_' if 'max_project' in image_type else ''}{folder_name}_raw.tif")
    image_output_name = os.path.join(processed_images_path, f"{'AVG_' if 'avg_project' in image_type else ''}{folder_name}_raw.tif")
    if os.path.exists(image_output_name):
        print(f"{folder_name} already exists!")
        log_details['Files Not Processed'].append(f'{folder_name}: Already exists!')
        return log_details
    
    if 'max_project' in image_type:
        axes = 'TCYX' 
    elif 'single_frame' in image_type: 
        axes = 'ZCYX' 
    else:
        axes = 'TZCYX'

    # Write the hyperstack to a TIFF file
    metadata = {
        'axes': axes,
        'finterval': frame_rate, 'unit': 'um',
        'mode': 'composite'
    }
    tifffile.imwrite(image_output_name, 
                    hyperstack, 
                    byteorder='>', 
                    imagej=True,
                    resolution=(1 / X_microns_per_pixel, 1 / Y_microns_per_pixel),
                    metadata=metadata, 
                    extratags=imagej_tags
                )
    
    # Prepare the column headers and values for laser power
    laser_power_headers = [f'{value.split(":")[-1].strip()} power' for value in laser_power_values.values()]
    laser_powers = [value.split(':')[1].split(',')[0].strip() for value in laser_power_values.values()]

    # Prepare the column headers and values for ND filters        
    nd_filter_headers = ['imaging light path', 'PA light path']
    nd_filter_values = [value.split(':')[-1].strip() for value in helios_nd_filter_values.values()]

    # Check if the file exists and create headers if not
    try:
        with open(metadata_csv_path, 'r') as file:
            existing_headers = file.readline().strip().split(',')
    except FileNotFoundError:
        existing_headers = []

    if not existing_headers:
        # Write the headers
        with open(metadata_csv_path, 'w', newline='') as file:
            csv_writer = csv.writer(file)
            headers = ["Folder Name", "X microns per pixel", "Z microns per pixel", 
                       "Frame Rate", "Bit Depth", "Dwell Time", 
                       "Objective Lens Description"] + laser_power_headers + nd_filter_headers
            csv_writer.writerow(headers)

    # Write metadata to CSV
    with open(metadata_csv_path, 'a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([folder_name, X_microns_per_pixel, Z_microns_per_pixel, frame_rate, 
                             bit_depth, dwell_time, objective_lens_description] + laser_powers + nd_filter_values)
    
    # Add folder name to log
    log_details['Files Processed'].append(folder_name)
    print(f"Successfully processed {folder_name}!")
    return log_details

def initialize_output_folders(parent_folder_path) -> tuple:
    '''
    Create the output folders for the processed images and the scope folders.
    '''
    processed_images_path = os.path.join(parent_folder_path, "!processed_images")
    os.makedirs(processed_images_path, exist_ok=True)
    scope_folders_path = os.path.join(parent_folder_path, "!scope_folders")
    os.makedirs(scope_folders_path, exist_ok=True)
    return processed_images_path, scope_folders_path

def setup_logging(processed_images_path) -> tuple:
    '''
    Set up the log file and parameters.
    '''
    log_file_path = os.path.join(processed_images_path, "!image_conversion_log.txt")
    log_details = {'Files Not Processed': [],
                   'Files Processed': [],
                   'Issues': []}
    return log_file_path, log_details