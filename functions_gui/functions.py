import os
import struct
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
    tree = ET.parse(xml_file)
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

def create_hyperstack(folder_path, max_project=False):
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
    all_files = []
    image_type = None

    #get all the files in the folder
    files_names = [file for file in os.listdir(folder_path) if file.endswith('.tif')]
    last_file_name = files_names[-1]
    single_plane = True if last_file_name.split('_')[-3] == 'Cycle00001' else False
    
    if not single_plane:
        # Get all files in the MIP folder
        mip_folder_path = os.path.join(folder_path, "MIP")
        files_in_mip = [os.path.join(mip_folder_path, file) for file in os.listdir(mip_folder_path)]

        # Check if a single timepoint was acquired
        last_file = files_in_mip[-1]
        single_timepoint = True if last_file.split('_')[-3] == 'Cycle00001' else False

        # Collect all files in the folder for specific image types
        if single_timepoint == True:
            if max_project == False:
                for file in os.listdir(folder_path):
                    if file.endswith(".tif"):
                        file_path = os.path.join(folder_path, file)
                        all_files.append(file_path)
                        image_type = "multi_plane_single_timepoint"
            else:
                all_files.extend(files_in_mip)
                image_type = "multi_plane_single_timepoint_max_project"
        else:
            if max_project == False:
                for file in os.listdir(folder_path):
                    if file.endswith(".tif"):
                        file_path = os.path.join(folder_path, file)
                        all_files.append(file_path)
                        image_type = "multi_plane_multi_timepoint"
            else:
                all_files.extend(files_in_mip)
                image_type = "multi_plane_multi_timepoint_max_project"

    # For single plane time series
    else:
        for file in os.listdir(folder_path):
            if file.endswith(".tif"):
                file_path = os.path.join(folder_path, file)
                all_files.append(file_path)
                image_type = "single_plane"

    # Sort files to ensure correct order
    all_files.sort()

    # Group files by channel
    channel_files = {}
    for file in all_files:
        channel_name = os.path.basename(file).split('_')[-2] 
        if channel_name not in channel_files:
            channel_files[channel_name] = []
        channel_files[channel_name].append(file)

    # Read images for each channel
    channel_images = {}
    for channel_name, files in channel_files.items():
        try:
            channel_images[channel_name] = [tifffile.imread(file, is_ome=False) for file in files]
        except Exception as e:
            print(f"Error reading TIFF file for channel {channel_name}: {e}")
            return None, None

    # Stack images for each channel
    stacked_images = {channel_name: np.stack(images) for channel_name, images in channel_images.items()}

    # Stack images across channels
    merged_images = np.stack(list(stacked_images.values()), axis=1)

    # Adjust axes based on image type
    if image_type == "multi_plane_multi_timepoint" or image_type == "multi_plane_single_timepoint":
        merged_images = np.moveaxis(merged_images, [0, 1, 2, 3, 4], [0, 2, 1, 3, 4])        
    if image_type == "single_plane":
        merged_images = np.moveaxis(merged_images, [0, 1, 2, 3, 4], [1, 2, 0, 3, 4])

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