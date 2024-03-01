import os
import tifffile
import numpy as np
import xml.etree.ElementTree as ET

def get_pixel_size(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    microns_per_pixel_element = root.find(".//PVStateValue[@key='micronsPerPixel']")
    microns_per_pixel = {}

    for indexed_value in microns_per_pixel_element.findall("./IndexedValue"):
        axis = indexed_value.attrib["index"]
        value = float(indexed_value.attrib["value"])
        microns_per_pixel[axis] = value 

    return microns_per_pixel['XAxis'], microns_per_pixel['YAxis']

def get_frame_rate(xml_file):
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
    directory: str, 
    logParams: dict
):
    '''
    Convert dictionary of parameters to a log file and save it in the directory
    '''
    logPath = os.path.join(directory, f"!image_conversion_log.txt")
    logFile = open(logPath, "w")                                    
    logFile.write("\n" + now.strftime("%Y-%m-%d %H:%M") + "\n")     
    for key, value in logParams.items():                            
        logFile.write('%s: %s\n' % (key, value))                    
    logFile.close()   

def create_hyperstack(folder_path):
    # convert and save the tiff stack
    all_files = []
    mip_folder_path = os.path.join(folder_path, "MIP")
    if os.path.exists(mip_folder_path) and os.path.isdir(mip_folder_path):
        files_in_mip = [os.path.join(mip_folder_path, file) for file in os.listdir(mip_folder_path)]
        all_files.extend(files_in_mip)

    channel_files = {}
    for file in all_files:
        channel_name = os.path.basename(file).split('_')[-2] 
        if channel_name not in channel_files:
            channel_files[channel_name] = []
        channel_files[channel_name].append(file)

    # Read images for each channel
    channel_images = {}
    for channel_name, files in channel_files.items():
        channel_images[channel_name] = [tifffile.imread(file) for file in files]

    # Stack images for each channel
    stacked_images = {}
    for channel_name, images in channel_images.items():
        stacked_images[channel_name] = np.stack(images)

    # Stack images across channels
    merged_images = np.stack(list(stacked_images.values()), axis=1)

    return merged_images
