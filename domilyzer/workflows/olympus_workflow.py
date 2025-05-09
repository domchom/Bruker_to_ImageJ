import os
from domilyzer.functions_gui.general_functions import (
    organizeFilesByChannel,
    saveImageJHyperstack
)
    
from domilyzer.functions_gui.olympus_functions import (
    generateChannelProjectionsOlympus, 
    stackChannelsGenHyperstackOlympus,
    extractTNumber
)    
    
def processOlympusImages(parent_folder_path: str,
                         processed_images_path: str,
                         microscope_type: str,
                         projection_type: str,
                         imagej_tags: dict,
                         image_folders: list = None
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
    
    for image_folder in image_folders:
        print('******'*10)
        print(f'Processing folder: {image_folder}')
        # get the folder path
        image_folder_path = os.path.join(parent_folder_path, image_folder)
        
        # extract metadata from the folder name, still need to be finished
        # extractMetadataFromPTYOlympus(image_folder_path)
        
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
        
        # print(f"Saving hyperstack to {hyperstack_output_path}...")
        print(f"Hyperstack shape: {hyperstack.shape}")
        print(f"ImageJ axes: {imageJAxes}")
        
        # Save the hyperstack
        saveImageJHyperstack(hyperstack, 
                        axes = imageJAxes,
                        metadata = None, # for now, flamingo data doesn't have metadata
                        image_output_name = hyperstack_output_path, 
                        imagej_tags = imagej_tags
                        )     
        
        print(f'Successfully processed {base_filename}')