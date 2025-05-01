import os
import re
import numpy as np
import tifffile

def get_channels_olympus(folder_path):
    # Collect the files corresponding to each channel and put in dict
    channel_files = {}
    for file in folder_path:
        channel_name = os.path.basename(file).split('_')[1][:4] 
        if channel_name not in channel_files:
            channel_files[channel_name] = []
        channel_files[channel_name].append(file)
        
    return channel_files    

def project_images_olympus(channel_files, projection_type='max'):
    # Sort the files in each channel by T number
    # This is done to ensure that the projection is done in the correct order
    for key in channel_files:
        channel_files[key].sort(key=extract_t_number) 
    
    projected_channel_files = {}
    for channel_name, files in channel_files.items():
        for file in files:
            if 'T' in file:
                # Extract the frame number from the filename
                frame_number = os.path.basename(file).split('T')[1][:3]
            if 'Z' in file:
                # Extract the z-plane number from the filename
                z_plane_number = os.path.basename(file).split('Z')[1][:3]
            if 'C' in file:
                # Extract the channel number from the filename
                channel_number = os.path.basename(file).split('C')[1][:3]
            # Find all files with the same frame number and channel, but unique Z
            matching_files = [
                f for f in files
                if f"T{frame_number}" in f and
                f"C{channel_number}" in f
            ]
            # Remove the matching files from the original list to avoid processing them again
            for f in matching_files:
                files.remove(f)
            # Read the images from the matching files
            images = [tifffile.imread(file, is_ome=False) for file in matching_files]
            # Stack the images along the Z axis
            images = np.stack(images, axis=0)
            # Perform the projection 
            if projection_type == 'max':
                projected_image = np.max(images, axis=0)
            # add projected images to the new dict
            if channel_name not in projected_channel_files:
                projected_channel_files[channel_name] = []
            projected_channel_files[channel_name].append(projected_image)
    return projected_channel_files
           
def extract_t_number(filename):
    match = re.search(r'T(\d+)', filename)
    return int(match.group(1)) if match else float('inf')    
    
def stack_channels_olympus(channel_images):
    # Ensure all channel image lists have the same length
    num_frames = 10000000 # Arbitrarily large number
    for channel_name, values in channel_images.items():
        channel_frames = len(values)
        if channel_frames < num_frames:
            num_frames = channel_frames
    
    for channel_name, values in channel_images.items():
        channel_images[channel_name] = values[:num_frames]
    
    merged_images = np.stack(list(channel_images.values()), axis=1)
    
    return merged_images