import os
import numpy as np
from domilyzer.functions_gui.general_functions import (
    organizeFilesByChannel,
    saveImageJHyperstack
)
    
from domilyzer.functions_gui.olympus_functions import (
    generateChannelProjectionsOlympus, 
    stackChannelsGenHyperstackOlympus,
    extractTNumber,
    extractMetadataFromOIFOlympus
)    
    
def processOlympusImages(parent_folder_path: str,
                         processed_images_path: str,
                         microscope_type: str,
                         projection_type: str,
                         imagej_tags: dict,
                         image_folders: list = None,
                         test = False
                         ) -> None:
    """
    Process Olympus images by organizing them into channels, generating projections, and saving them as hyperstacks.
    
    Parameters:
    - parent_folder_path (str): Path to the parent folder containing the image folders.
    - processed_images_path (str): Path to save the processed images.
    - microscope_type (str): Type of microscope used for imaging.
    - projection_type (str): Type of projection to be used ('max', 'avg', or None).
    - imagej_tags (dict): Tags to be used for saving the images in ImageJ format.
    - image_folders (list): List of image folders to process. If None, all folders in the parent folder will be processed.
    """
    
    hyperstack_arrays = [] # List to store shapes of hyperstacks for testing
    print(image_folders)
    
    for image_folder in image_folders:
        print('******'*10)
        print(f'Processing folder: {image_folder}')
        # get the folder path
        image_folder_path = os.path.join(parent_folder_path, image_folder)
        
        # Find the matching .oif file path in the parent folder
        OIFfilepath = None
        for root, dirs, files in os.walk(parent_folder_path):
            for file in files:
                if file.endswith(".oif") and os.path.basename(file).replace(".oif", ".oif.files") == image_folder:
                    OIFfilepath = os.path.join(root, file)
                    break
            if OIFfilepath:
                break
            
        # extract metadata from the folder name
        metadata = {}
        total_time_sec, pixel_width, pixel_unit = extractMetadataFromOIFOlympus(file_path=OIFfilepath)
        metadata['X_microns_per_pixel'] = pixel_width
        metadata['Y_microns_per_pixel'] = pixel_width
        metadata['pixel_unit'] = pixel_unit
        # calculate the frame interval later once we know the shape of the hyperstack
        
        # get all tiff files in the folder
        tif_filenames = [file for file in os.listdir(image_folder_path) if file.endswith('.tif') and file.startswith('s') and not any(r in file for r in ['-R001', '-R002', '-R003', '-R004'])]
        folder_tif_filenames = [os.path.join(image_folder_path, file) for file in tif_filenames]
        
        # organize the files into channels
        channel_filenames = organizeFilesByChannel(folder_tif_filenames=folder_tif_filenames,
                                                    microscope_type=microscope_type)
        
        # Sort the files in each channel by T number
        # This is done to ensure that the projection is done in the correct order
        for key in channel_filenames:
            channel_filenames[key].sort(key=extractTNumber) 
        
        # organize and project the images for each channel
        channel_image_arrays, image_type = generateChannelProjectionsOlympus(channel_filenames=channel_filenames, 
                                                                    projection_type=projection_type)
                    
        # Stack the images for each channel, then combine them into a hyperstack
        hyperstack = stackChannelsGenHyperstackOlympus(channel_image_arrays=channel_image_arrays)
        
        # Create the output path for the final hyperstack
        base_filename = os.path.basename(image_folder_path).replace(".oif.files", "")
        base_filename = "MAX_" + base_filename if projection_type == 'max' else "AVG_" + base_filename if projection_type == 'avg' else base_filename
        hyperstack_output_path = os.path.join(processed_images_path, f"{base_filename}_raw.tif")
        
        # reshape the hyperstack to be in the correct format for imagej
        if projection_type is None:
            hyperstack = hyperstack.transpose(0, 2, 1, 3, 4)
            imageJAxes = 'TZCYX'
            
        if 'singleframe' in image_type and projection_type is not None:
            imageJAxes = 'ZCYX'
            
        elif 'multiframe' in image_type and projection_type is None:
            imageJAxes = 'TZCYX'
            
        elif 'multiframe' in image_type and projection_type is not None:
            imageJAxes = 'TCYX'
            
        hyperstack_arrays.append(hyperstack) # Append the shape of the hyperstack for testing
        
        if test == False:
            # print(f"Saving hyperstack to {hyperstack_output_path}...")
            print(f"Hyperstack shape: {hyperstack.shape}")
            
            # calculate the frame interval in seconds
            frame_interval = total_time_sec / hyperstack.shape[0] if 'singleframe' not in image_type else 0
            metadata['framerate'] = frame_interval
            
            # Save the hyperstack
            saveImageJHyperstack(hyperstack, 
                            axes = imageJAxes,
                            metadata = metadata,
                            image_output_name = hyperstack_output_path, 
                            imagej_tags = imagej_tags
                            )     
        
        print(f'Successfully processed {base_filename}')
        
        # Save the list of hyperstack arrays as a numpy file for testing
        '''if test == True and projection_type == None:
            hyperstack_save_path = os.path.join('/Users/domchom/Downloads', "hyperstack_arrays.npz")
            # Save each array with a unique key
            np.savez_compressed(hyperstack_save_path, **{f'array_{i}': arr for i, arr in enumerate(hyperstack_arrays)})
            print(f"Hyperstack arrays saved to {hyperstack_save_path}")'''
        
    return hyperstack_arrays