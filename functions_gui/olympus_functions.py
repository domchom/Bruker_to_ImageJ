import os
import re
import numpy as np
import tifffile


def generateChannelProjectionsOlympus(channel_filenames: dict, 
                                      projection_type: str ='max'
                                      ) -> tuple:
    """
    Generate channel projections for Olympus images based on the provided filenames.
    
    Parameters:
    channel_filenames (dict): Dictionary where keys are channel names and values are lists of file paths.
    projection_type (str): Type of projection to apply ('max', 'avg', or 'raw').
    
    Returns:
    dict: A dictionary where keys are channel names and values are lists of numpy arrays.
    str: The type of image generated based on the projection.
    """    
    final_channel_image_arrays = {}
    for channel_name, filenames in channel_filenames.items():
        # create a set to keep track of processed files to avoid duplicates
        # and to ensure we only process each file once
        processed_files = set()
        # Find the highest Z number in the whole list of filenames
        all_z_numbers = [
            extractZNumber(f) for f in filenames if extractZNumber(f) != float('inf')
        ]
        z_planes_per_frame = max(all_z_numbers) if all_z_numbers else 0
        for filename in filenames:
            if filename in processed_files:
                continue  # Skip files we've already processed
            # Extract identifiers
            basename = os.path.basename(filename).replace('.tif',"")
            frame_number = os.path.basename(filename).split('T')[1][:3] if 'T' in basename else None
            z_plane_number = os.path.basename(filename).split('Z')[1][:3] if 'Z' in basename else None 
            channel_number = os.path.basename(filename).split('C')[1][:3] if 'C' in basename else None
            # Find the matching files based on whether identifiers are present
            if frame_number and channel_number and z_plane_number:
                matching_files = [
                    f for f in filenames if f"T{frame_number}" in f and f"C{channel_number}" in f
                ]
                image_type = 'multiplane_multiframe' 
            elif frame_number and channel_number and not z_plane_number:
                matching_files = [
                    f for f in filenames if f"T{frame_number}" in f and f"C{channel_number}" in f
                ]
                image_type = 'singleplane_multiframe'
            elif not frame_number and channel_number and z_plane_number:
                matching_files = [
                    f for f in filenames if f"C{channel_number}" in f
                ]
                image_type = 'multiplane_singleframe'
            elif not frame_number and channel_number and not z_plane_number:
                matching_files = [
                    f for f in filenames if f"C{channel_number}" in f
                ]
                image_type = 'singleplane_singleframe'
                        
            # Mark files as processed
            processed_files.update(matching_files)
            
            # sort the matching files by Z number to ensure correct stacking
            matching_files = sorted(matching_files, key=extractZNumber)
            if len(matching_files) != z_planes_per_frame and z_planes_per_frame != 0:
                continue  # Skip if the number of matching files is not consistent
            
            # Read the images from the matching files
            images = [tifffile.imread(file, is_ome=False) for file in matching_files]
            # Stack the images along the Z axis
            images = np.stack(images, axis=0)
            # Perform the projection if requested
            if 'single_plane' not in image_type:
                if projection_type == 'max':
                    images = np.max(images, axis=0)
                    image_type = image_type + '_maxproject'
                elif projection_type == 'avg':
                    images = np.mean(images, axis=0)
                    images = np.round(images).astype(np.uint16) 
                    image_type = image_type + '_avgproject'
                else:
                    image_type = image_type + '_raw'
            
            # Check if the channel name already exists in the dictionary
            # and append the images to the list
            if channel_name not in final_channel_image_arrays:
                final_channel_image_arrays[channel_name] = []
            final_channel_image_arrays[channel_name].append(images)
            
    return final_channel_image_arrays, image_type

def getMaxZPlanes(filenames: list) -> int:
    """
    Get the maximum number of Z planes from a list of filenames.
    
    Parameters:
    filenames (list): List of filenames to extract Z numbers from.
    
    Returns:
    int: The maximum number of Z planes found in the filenames.
    """
    all_z_numbers = [extractZNumber(f) for f in filenames if extractZNumber(f) != float('inf')]
    z_planes_per_frame = max(all_z_numbers) if all_z_numbers else 0
    return z_planes_per_frame

def extractIdentifiers(filename: str) -> tuple:
    """
    Extract the identifiers from the filename.
    
    Parameters:
    filename (str): The filename to extract identifiers from.
    
    Returns:
    tuple: A tuple containing the frame number, Z plane number, and channel number.
    """
    basename = os.path.basename(filename).replace('.tif', "")
    frame_number = basename.split('T')[1][:3] if 'T' in basename else None
    z_plane_number = basename.split('Z')[1][:3] if 'Z' in basename else None
    channel_number = basename.split('C')[1][:3] if 'C' in basename else None
    return frame_number, z_plane_number, channel_number

def getMatchingFiles(filenames: list, 
                     frame_number: str, 
                     z_plane_number: str, 
                     channel_number: str) -> tuple:
    """
    Get the matching files based on the provided identifiers.
    
    Parameters:
    filenames (list): List of filenames to search for matches.
    frame_number (str): The frame number to match.
    z_plane_number (str): The Z plane number to match.
    channel_number (str): The channel number to match.
    
    Returns:
    tuple: A tuple containing the list of matching files and the type of image generated.
    """
    if frame_number and channel_number and z_plane_number:
        matching_files = [
            f for f in filenames if f"T{frame_number}" in f and f"C{channel_number}" in f
        ]
        image_type = 'multiplane_multiframe' 
    elif frame_number and channel_number and not z_plane_number:
        matching_files = [
            f for f in filenames if f"T{frame_number}" in f and f"C{channel_number}" in f
        ]
        image_type = 'singleplane_multiframe'
    elif not frame_number and channel_number and z_plane_number:
        matching_files = [
            f for f in filenames if f"C{channel_number}" in f
        ]
        image_type = 'multiplane_singleframe'
    elif not frame_number and channel_number and not z_plane_number:
        matching_files = [
            f for f in filenames if f"C{channel_number}" in f
        ]
        image_type = 'singleplane_singleframe'
        
    return matching_files, image_type
            
def loadAndProjectImages(matching_files: list, 
                         image_type: str, 
                         projection_type: str) -> tuple:
    """
    Load and project images based on the matching files and projection type.
    
    Parameters:
    matching_files (list): List of matching file paths.
    image_type (str): Type of image to generate.
    projection_type (str): Type of projection to apply ('max', 'avg', or 'raw').
    
    Returns:
    np.ndarray: The projected image.
    str: The type of image generated based on the projection.
    """
    # Read the images from the matching files
    images = [tifffile.imread(file, is_ome=False) for file in matching_files]
    # Stack the images along the Z axis
    images = np.stack(images, axis=0)
    # Perform the projection if requested
    if 'single_plane' not in image_type:
        if projection_type == 'max':
            images = np.max(images, axis=0)
            image_type = image_type + '_maxproject'
        elif projection_type == 'avg':
            images = np.mean(images, axis=0)
            images = np.round(images).astype(np.uint16) 
            image_type = image_type + '_avgproject'
        else:
            image_type = image_type + '_raw'
    
    return images, image_type
        
               
def extractTNumber(filename: str) -> int:
    """
    Extract the T number from the filename.
    
    Parameters:
    filename (str): The filename to extract the T number from.
    
    Returns:
    int: The extracted T number, or float('inf') if not found.
    """
    match = re.search(r'T(\d+)', filename)
    return int(match.group(1)) if match else float('inf')    

def extractZNumber(filename: str) -> int:
    """
    Extract the Z number from the filename.
    
    Parameters:
    filename (str): The filename to extract the Z number from.
    
    Returns:
    int: The extracted Z number, or float('inf') if not found.
    """
    match = re.search(r'Z(\d+)', filename)
    return int(match.group(1)) if match else float('inf')
    
def stackChannelsGenHyperstackOlympus(channel_image_arrays: dict) -> np.ndarray:
    """
    Stack the channel images into a hyperstack format.
    
    Parameters:
    channel_image_arrays (dict): Dictionary where keys are channel names and values are lists of numpy arrays.
    
    Returns:
    np.ndarray: A numpy array representing the stacked hyperstack.
    """
    # Ensure all channel image lists have the same length
    num_frames = 10000000 # Arbitrarily large number
    for channel_name, image_arrays in channel_image_arrays.items():
        channel_frames = len(image_arrays)
        if channel_frames < num_frames:
            num_frames = channel_frames
    
    for channel_name, image_arrays in channel_image_arrays.items():
        channel_image_arrays[channel_name] = image_arrays[:num_frames]
        
    merged_images = np.stack(list(channel_image_arrays.values()), axis=1)
    
    return merged_images

def extractMetadataFromPTYOlympus(folder_path: str) -> float:
    """
    Extract the 'Time Per Series' value from the latest .pty file in the specified folder.
    
    Parameters:
    folder_path (str): The path to the folder containing .pty files.
    
    Returns:
    
    """
    pty_files = [
        f for f in os.listdir(folder_path)
        if f.endswith('.pty') and f.startswith('s') and not any(r in f for r in ['-R001', '-R002', '-R003', '-R004', 'Thumb'])
    ]
    if not pty_files:
        raise FileNotFoundError("No matching .pty files found in the folder.")

    # Sort the files by T number and Z number to ensure we get the last one
    pty_files = sorted(pty_files)
    pty_files = sorted(pty_files, key=extractZNumber)
    pty_files = sorted(pty_files, key=extractTNumber)

    final_pty = pty_files[-1]

    with open(os.path.join(folder_path, final_pty), 'r') as file:
        for line in file:
            if 'Time Per Series' in line:
                total_time = float(line.split('=')[1].strip().replace('"', ''))
                print(total_time)
                return total_time

    raise ValueError("'Time Per Series' not found in the file.")