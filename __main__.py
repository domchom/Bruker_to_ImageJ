import os
import timeit
import shutil
import numpy as np
from functions_gui.gui import BaseGUI, FlamingoGUI, OlympusGUI
from functions_gui.general_functions import (
    initializeOutputFolders,
    initializeLogFile,
    adjustImageJAxes,
    saveLogFile,
    saveImageJHyperstack,
    createImageJMetadataTags
)
from functions_gui.bruker_functions import (
    determineImageTypeBruker,
    organizeFilesByChannelBruker,
    convertImagesToNumpyArraysBruker,
    adjustNumpyArrayAxesBruker,
    projectNumpyArraysBruker,
    writeMetadataCsvBruker,
    extractMetadataFromXMLBruker,   
)
from functions_gui.flamingo_functions import (
    organizeFilesByChannelFlamingo,
    getNumFramesFlamingo,
    getNumIlluminationSidesFlamingo,
    convertImagesToNumpyArraysAndProjectFlamingo,
    mergeNumpyArrayIlluminationSidesFlamingo
)

from functions_gui.olympus_functions import (
    get_channels_olympus,
    stack_channels_olympus,
    project_images_olympus,
    extract_t_number,
    extract_metadata_olympus
)

def main():
    # Bruker GUI
    gui = BaseGUI()
    gui.mainloop()
    
    # Get GUI variables
    parent_folder_path = gui.folder_path
    avg_projection = gui.avg_project
    max_projection = gui.max_project
    single_plane = gui.single_plane
    ch1_lut = gui.channel1_var
    ch2_lut = gui.channel2_var
    ch3_lut = gui.channel3_var
    ch4_lut = gui.channel4_var
    microscope_type = gui.microscope_type
    auto_metadata_extract = gui.auto_metadata_extraction
    
    # If user specifies Flamingo workflow, run Flamingo GUI
    if microscope_type == 'Flamingo':
        gui = FlamingoGUI()
        gui.mainloop()
        
        # Get GUI variables
        parent_folder_path = gui.folder_path
        avg_projection = gui.avg_project
        max_projection = gui.max_project
        ch1_lut = gui.channel1_var
        ch2_lut = gui.channel2_var
        ch3_lut = gui.channel3_var
        ch4_lut = gui.channel4_var
        microscope_type = gui.microscope_type
        
    # If user specifies Olympus workflow, run Olympus GUI
    if microscope_type == 'Olympus':
        gui = OlympusGUI()
        gui.mainloop()

        # Get GUI variables
        parent_folder_path = gui.folder_path
        avg_projection = gui.avg_project
        max_projection = gui.max_project
        single_plane = gui.single_plane
        ch1_lut = gui.channel1_var
        ch2_lut = gui.channel2_var
        ch3_lut = gui.channel3_var
        ch4_lut = gui.channel4_var
        microscope_type = gui.microscope_type
        
    # Performance tracker
    start_time = timeit.default_timer()

    # Check if neither max nor avg projection are selected, default to saving full hyperstacks
    if not avg_projection and not max_projection:
        print('Neither max nor avg projection selected. Saving full hyperstacks. This might take a while!')
        projection = None
    elif max_projection:
        print('Max projection selected. Saving max projections.')
        projection = 'max'
    elif avg_projection:
        print('Avg projection selected. Saving avg projections.')
        projection = 'avg'
        
    # Create a dictionary of imagej metadata tags
    imagej_tags = createImageJMetadataTags({'LUTs': [ch1_lut, ch2_lut, ch3_lut, ch4_lut]}, '>')
    
    # Determine the microscope type # TODO: need to fully implement this function once olympus function is finished
    # microscope_type = determine_scope(image_folders[0])

    # BRUKER WORKFLOW
    if microscope_type == 'Bruker':
        # Get the Bruker image folders
        image_folders = sorted([folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))])

        # TODO: MOVE OUTSIDE OF MAIN FUNCTION when done testing olympus functions
        # Initialize output folders, logging, and metadata CSV outout paths
        processed_images_path, scope_folders_path = initializeOutputFolders(parent_folder_path)
        log_file_path, log_details = initializeLogFile(processed_images_path)
        metadata_csv_path = os.path.join(processed_images_path, "!image_metadata.csv")

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
                        extracted_metadata, log_details = extractMetadataFromXMLBruker(xml_file_path, log_details)
                else:
                    log_details['Other Notes'].append(f'Skipping metadata extraction {folder_name}.')
                    extracted_metadata = None
                    
                # Determine the image type (single plane, max projection, or avg projection) and return all the TIF files in the folder as a list
                image_type, folder_tif_files = determineImageTypeBruker(folder_path, projection, single_plane)    
                
                # Collect the files corresponding to each channel and put in dict
                channel_files = organizeFilesByChannelBruker(folder_tif_files)
                
                # Stack the images for each channel, then combine them into a hyperstack
                channel_images = convertImagesToNumpyArraysBruker(channel_files)
                
                # Stack the images for each channel
                stacked_images = {channel_name: np.stack(images) for channel_name, images in channel_images.items()}

                # Stack images across channels
                hyperstack = np.stack(list(stacked_images.values()), axis=1)
    
                # Adjust axes for the hyperstack depending on the image type, and return the adjusted image type
                hyperstack, image_type = adjustNumpyArrayAxesBruker(hyperstack, image_type)
                
                # Project the images if max or avg projection is selected
                hyperstack = projectNumpyArraysBruker(hyperstack, image_type, projection)
                
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
                axes = adjustImageJAxes(image_type)
                
                # Save the hyperstack
                saveImageJHyperstack(hyperstack, axes, extracted_metadata, image_output_name, imagej_tags)
                
                # Create metadata for the hyperstack, and update the log file to save after all folders are processed
                log_details = writeMetadataCsvBruker(extracted_metadata, metadata_csv_path, folder_name, log_details)
                    
            except Exception as e:
                log_details['Files Not Processed'].append(f'{folder_name}: {e}')
                print(f"Error processing {folder_name}!")
                pass
                                
        for folder_name in image_folders:
            shutil.move(os.path.join(parent_folder_path, folder_name), os.path.join(scope_folders_path, folder_name))

        end_time = timeit.default_timer()
        log_details["Time Elapsed"] = f"{end_time - start_time:.2f} seconds"
        print(f'Time elapsed: {end_time - start_time:.2f} seconds')
        
        # Save the log file
        saveLogFile(log_file_path, log_details)
    
    # FLAMINGO WORKFLOW
    elif microscope_type == 'Flamingo':
        # Get the list of all TIF files in the directory
        tif_files = [f for f in os.listdir(parent_folder_path) if f.endswith('.tif') and f.startswith('S')]
        # for reference filename structure: S000_t000000_V000_R0000_X000_Y000_C00_I0_D0_P00366
        # S: unsure, t: time point, V: unsure, R: rotation, X: x position, 
        # Y: y position, C: channel, I: illumination side, D: unsure, P: Z-planes

        # Get the number of channels and frames
        num_channels, channels = organizeFilesByChannelFlamingo(tif_files)
        num_frames = getNumFramesFlamingo(tif_files)
        num_illumination_sides = getNumIlluminationSidesFlamingo(tif_files)
        print(f"Number of channels: {num_channels}")
        print(f"Number of frames: {num_frames}")
        print(f"Number of illumination sides: {num_illumination_sides}")

        # Read all TIF files and Z-project them (if desired)
        all_images = convertImagesToNumpyArraysAndProjectFlamingo(parent_folder_path, tif_files, projection)

        # Create the final hyperstack that will hold all frames
        final_hyperstack = mergeNumpyArrayIlluminationSidesFlamingo(all_images, 
                                                                tif_files, 
                                                                num_frames, 
                                                                num_channels, 
                                                                channels, 
                                                                projection
                                                                )

        # Create output path for the final hyperstack
        folder_name = os.path.basename(parent_folder_path)
        name_suffix = 'MAX' if projection == 'max' else 'AVG' if projection == 'avg' else 'hyperstack'
        hyperstack_output_path = f'{parent_folder_path}/{folder_name}_{name_suffix}.tif'
        
        # Check if the output file already exists
        if os.path.exists(hyperstack_output_path):
            print(f"Output file {hyperstack_output_path} already exists. Overwriting...")
            # Remove the existing file
            os.remove(hyperstack_output_path)
        
        # Create axes metadata for the hyperstack
        axes = 'TCYX' if projection == 'max' or projection == 'avg' else 'TZCYX'
            
        # Calculate the size of the final hyperstack in bytes, and warn if it's too large
        # 1 GB = 1024^3 bytes
        final_hyperstack_size = final_hyperstack.nbytes
        if final_hyperstack_size > (1024 ** 3):
            print(f"Warning: The final hyperstack is {final_hyperstack_size / (1024 ** 3):.2f} GB. It may take a while to save.")
            print("Consider splitting the data into smaller chunks.")
            
        print(f"Saving hyperstack to {hyperstack_output_path}...")
        
        # Save the hyperstack
        saveImageJHyperstack(final_hyperstack, 
                        axes,
                        metadata = None, # for now, flamingo data doesn't have metadata
                        image_output_name = hyperstack_output_path, 
                        imagej_tags = imagej_tags
                        ) 

        print(f'Successfully saved hyperstack to {hyperstack_output_path}')
        
        end_time = timeit.default_timer()
        print(f'Time elapsed: {end_time - start_time:.2f} seconds')
        
    elif microscope_type == 'Olympus':
        image_folders = sorted([folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))])
        
        # Initialize output folders, logging, and metadata CSV outout paths
        #processed_images_path, scope_folders_path = initialize_output_folders(parent_folder_path)

        for folder_name in image_folders:
            print('******'*10)
            print(f'Processing folder: {folder_name}')
            # get the folder path
            folder_path = os.path.join(parent_folder_path, folder_name)
            
            # extract metadata from the folder name
            extract_metadata_olympus(folder_path)
            
            # get all tiff files in the folder
            tif_files = [f for f in os.listdir(folder_path) if f.endswith('.tif') and f.startswith('s') and not any(r in f for r in ['-R001', '-R002', '-R003', '-R004'])]
            folder_tif_files = [os.path.join(folder_path, file) for file in tif_files]
            
            # organize the files into channels
            channel_files = get_channels_olympus(folder_tif_files)
            
            # Sort the files in each channel by T number
            # This is done to ensure that the projection is done in the correct order
            for key in channel_files:
                channel_files[key].sort(key=extract_t_number) 
            
            # organize and project the images for each channel
            final_channel_files = project_images_olympus(channel_files, projection)
                        
            # Stack the images for each channel, then combine them into a hyperstack
            hyperstack = stack_channels_olympus(final_channel_files)
            
            # Create the output path for the final hyperstack
            filename = os.path.basename(folder_path).replace(".oif.files", "")
            hyperstack_output_path = os.path.join(parent_folder_path, f"{filename}_raw.tif")
            hyperstack_output_path = "MAX_" + hyperstack_output_path if projection == 'max' else "AVG_" + hyperstack_output_path if projection == 'avg' else hyperstack_output_path
            
            # reshape the hyperstack to be in the correct format for imagej
            if projection is None:
                hyperstack = hyperstack.transpose(0, 2, 1, 3, 4)
            
            print(f"Hyperstack shape: {hyperstack.shape}")
            print(f"Saving hyperstack to {hyperstack_output_path}...")
            
            # Save the hyperstack
            saveImageJHyperstack(hyperstack, 
                            axes = 'TZCYX' if projection is None else 'TCYX',
                            metadata = None, # for now, flamingo data doesn't have metadata
                            image_output_name = hyperstack_output_path, 
                            imagej_tags = imagej_tags
                            )             
              
if __name__ == '__main__':
    main()

print('Done with script!')
