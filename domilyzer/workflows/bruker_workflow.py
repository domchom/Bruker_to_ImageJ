import os
import numpy as np
from domilyzer.functions_gui.bruker_functions import (
    determineImageTypeBruker,
    extractMetadataFromXMLBruker,
    convertImagesToNumpyArraysBruker,
    adjustNumpyArrayAxesBruker,
    projectNumpyArraysBruker,
    writeMetadataCsvBruker
    )

from domilyzer.functions_gui.general_functions import (
    organizeFilesByChannel,
    adjustImageJAxes,
    saveImageJHyperstack,
)

def processBrukerImages(parent_folder_path: str,
                        image_folders: list,
                        processed_images_path: str,
                        metadata_csv_path: str,
                        microscope_type: str,
                        projection_type: str,
                        single_plane: bool,
                        auto_metadata_extract: bool,
                        test: bool =False,
                        imagej_tags: dict =None,
                        log_details: dict =None
                        ) -> dict:
    """
    Process Bruker images from a parent folder, extract metadata, and save as ImageJ hyperstack.
    
    Parameters:
    - parent_folder_path (str): Path to the parent folder containing image folders.
    - processed_images_path (str): Path to save processed images.
    - metadata_csv_path (str): Path to save metadata CSV.
    - microscope_type (str): Type of microscope used.
    - projection_type (str): Type of projection to apply ('max_project' or 'avg_project').
    - single_plane (bool): Whether the images are single plane.
    - auto_metadata_extract (bool): Whether to automatically extract metadata from XML files.
    - test (bool): If True, run in test mode (no file writing).
    - imagej_tags (dict): Additional tags for ImageJ metadata.
    
    Returns:
    - log_details (dict): Log details including processed and not processed files.
    """
    hyperstack_arrays = [] # List to store shapes of hyperstacks for testing
    
    for folder_name in image_folders:
        print('******'*10)
        try:
            print(f'Processing folder: {folder_name}')
            # get the folder path
            folder_path = os.path.join(parent_folder_path, folder_name)
            if auto_metadata_extract:
                # Check for XML file and extract relevant metadata
                xml_files = [file for file in os.listdir(folder_path) if os.path.splitext(file)[1] == ".xml"]   
                if not xml_files:
                    raise FileNotFoundError(f"No XML file found in folder {folder_name}")
                else:
                    xml_file_path = os.path.join(folder_path, xml_files[0])
                    extracted_metadata, log_details = extractMetadataFromXMLBruker(xml_file_path = xml_file_path, 
                                                                                    log_params = log_details)
            else:
                log_details['Other Notes'].append(f'Skipping metadata extraction {folder_name}.')
                extracted_metadata = None
                
            # Determine the image type (single plane, max projection, or avg projection) and return all the TIF files in the folder as a list
            image_type, folder_tif_file_ames = determineImageTypeBruker(folder_path=folder_path, 
                                                                        projection_type=projection_type, 
                                                                        single_plane=single_plane)    
            
            # Collect the files corresponding to each channel and put in dict
            channel_filenames = organizeFilesByChannel(folder_tif_filenames=folder_tif_file_ames,
                                                        microscope_type=microscope_type)
            
            # Stack the images for each channel, then combine them into a hyperstack
            channel_image_arrays = convertImagesToNumpyArraysBruker(channel_filenames=channel_filenames)
            
            # Stack the images for each channel
            stacked_image_arrays = {channel_name: np.stack(arrays) for channel_name, arrays in channel_image_arrays.items()}

            # Stack images across channels
            hyperstack = np.stack(list(stacked_image_arrays.values()), axis=1)

            # Adjust axes for the hyperstack depending on the image type, and return the adjusted image type
            hyperstack, image_type = adjustNumpyArrayAxesBruker(hyperstack=hyperstack, image_type=image_type)
            
            # Project the images if max or avg projection is selected
            hyperstack = projectNumpyArraysBruker(hyperstack=hyperstack, 
                                                    image_type=image_type, 
                                                    projection_type=projection_type)
            
            if auto_metadata_extract is True:
                # Recalculate the frame rate for single plane: divide by number of frames
                extracted_metadata['framerate'] = extracted_metadata['framerate'] / hyperstack.shape[0] if 'single_plane' in image_type else extracted_metadata['framerate']
                            
            # create the output image name
            prefix = "MAX_" if "max_project" in image_type else "AVG_" if "avg_project" in image_type else ""
            image_output_name = os.path.join(processed_images_path, f"{prefix}{folder_name}_raw.tif")
            if os.path.exists(image_output_name):
                print(f"{folder_name} already exists!")
                log_details['Files Not Processed'].append(f'{folder_name}: Already exists!')
                return log_details
            
            # determine the axes for the hyperstack
            imageJ_axes = adjustImageJAxes(image_type=image_type)
            
            hyperstack_arrays.append(hyperstack) # Append the shape of the hyperstack for testing

            # Save the hyperstack
            if test == False:
                
                saveImageJHyperstack(hyperstack=hyperstack, 
                                        axes=imageJ_axes, 
                                        metadata=extracted_metadata, 
                                        image_output_name=image_output_name, 
                                        imagej_tags=imagej_tags
                                        )
            
                # Create metadata for the hyperstack, and update the log file to save after all folders are processed
                log_details = writeMetadataCsvBruker(metadata=extracted_metadata, 
                                                    metadata_csv_path=metadata_csv_path, 
                                                    folder_name=folder_name, 
                                                    log_details=log_details
                                                    )
                            
        except Exception as e:
            log_details['Files Not Processed'].append(f'{folder_name}: {e}')
            print(f"Error processing {folder_name}!: {e}")
            pass
        
    
    # Save the list of hyperstack arrays as a numpy file
    if test == True:
        hyperstack_save_path = os.path.join('/Users/domchom/Downloads', "hyperstack_arrays.npz")
        # Save each array with a unique key
        np.savez_compressed(hyperstack_save_path, **{f'array_{i}': arr for i, arr in enumerate(hyperstack_arrays)})
        print(f"Hyperstack arrays saved to {hyperstack_save_path}")
            
    return log_details, hyperstack_arrays