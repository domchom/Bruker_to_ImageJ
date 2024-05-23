import os
import tifffile
import numpy as np
import xml.etree.ElementTree as ET

# TODO: and the ability to import movies from the lightsheet and FV
# TODO: add the ability to create MIPs and save them if no MIPs already exist
# TODO: add the ability to import single plane images (although this might already work)
# TODO: add the ability to import single timepoint z stacks (although this might already work)0


def get_pixel_size(xml_file):
    """
    Retrieves the pixel size in microns from an XML file.

    Parameters:
        xml_file (str): The path to the XML file.

    Returns:
        tuple: A tuple containing the pixel size in microns for the X, Y, and Z axes respectively.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    microns_per_pixel_element = root.find(".//PVStateValue[@key='micronsPerPixel']")
    microns_per_pixel = {}

    for indexed_value in microns_per_pixel_element.findall("./IndexedValue"):
        axis = indexed_value.attrib["index"]
        value = float(indexed_value.attrib["value"])
        microns_per_pixel[axis] = value 

    return microns_per_pixel['XAxis'], microns_per_pixel['YAxis'], microns_per_pixel['ZAxis']

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

    # get the bit depth
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

    return bit_depth, dwell_time, helios_nd_filter_values, laser_power_values, objective_lens_description, log_params

def get_frame_rate(xml_file):
    """
    Calculate the frame rate of a video based on the provided XML file.

    Parameters:
        xml_file (str): The path to the XML file containing the video metadata.

    Returns:
        float: The frame rate of the video.
    """

    tree = ET.parse(xml_file)
    root = tree.getroot()

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

    return framerate

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

    # Check to see if multiple stacks were acquired
    mip_folder_path = os.path.join(folder_path, "MIP")
    if os.path.exists(mip_folder_path) and os.path.isdir(mip_folder_path):
        files_in_mip = [os.path.join(mip_folder_path, file) for file in os.listdir(mip_folder_path)]
        # If a single timepoint, and do not want to create a max projection
        if len(files_in_mip) < 5 and max_project == False: #TODO: This is a hacky way to determine if it's a single timepoint
            for file in os.listdir(folder_path):
                if file.endswith(".tif"):
                    file_path = os.path.join(folder_path, file)
                    all_files.append(file_path)
                    image_type = "multi_plane_single_timepoint"
        elif len(files_in_mip) < 5 and max_project == True:
            all_files.extend(files_in_mip)
            image_type = "multi_plane_single_timepoint_max_project"
        # If a time series, max projection is not desired
        elif len(files_in_mip) > 5 and max_project == False:
            for file in os.listdir(folder_path):
                if file.endswith(".tif"):
                    file_path = os.path.join(folder_path, file)
                    all_files.append(file_path)
                    image_type = "multi_plane_multi_timepoint"
        # If a time series, max projection is desired
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

    all_files = sorted(all_files)

    # Group files by channel
    channel_files = {}
    for file in all_files:
        channel_name = os.path.basename(file).split('_')[-2] 
        if channel_name not in channel_files:
            channel_files[channel_name] = []
        channel_files[channel_name].append(file)

    channel_images = {}
    for channel_name, files in channel_files.items():
        channel_images[channel_name] = [tifffile.imread(file, is_ome=False) for file in files]

    # Stack images for each channel
    stacked_images = {}
    for channel_name, images in channel_images.items():
        stacked_images[channel_name] = np.stack(images)

    # Stack images across channels
    merged_images = np.stack(list(stacked_images.values()), axis=1)

    if image_type == "multi_plane_multi_timepoint":
        merged_images = np.moveaxis(merged_images, [0, 1, 2, 3, 4], [0, 2, 1, 3, 4])
        pass

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