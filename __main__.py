import os
import timeit
import shutil
import numpy as np
from functions_gui.gui import BaseGUI, FlamingoGUI, OlympusGUI
from functions_gui.general_functions import (
    initializeOutputFolders,
    initializeLogFile,
    saveLogFile,
    saveImageJHyperstack,
    createImageJMetadataTags,
)

from workflows.bruker_workflow import processBrukerImages
from workflows.olympus_workflow import processOlympusImages
from functions_gui.flamingo_functions import (
    getNumChannelsFlamingo,
    getNumFramesFlamingo,
    getNumIlluminationSidesFlamingo,
    convertImagesToNumpyArraysAndProjectFlamingo,
    mergeNumpyArrayIlluminationSidesFlamingo
)


def main():
    test = False # Set to True for testing purposes, will skip GUI and use test data. Also will not move folders to processed images folder.
    
    if not test:
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
            
    else: 
        # For testing purposes, set the parameters directly
        red = np.zeros((3, 256), dtype='uint8')
        red[0] = np.arange(256, dtype='uint8')

        green = np.zeros((3, 256), dtype='uint8')
        green[1] = np.arange(256, dtype='uint8')

        blue = np.zeros((3, 256), dtype='uint8')
        blue[2] = np.arange(256, dtype='uint8')

        magenta = np.zeros((3, 256), dtype='uint8')
        magenta[0] = np.arange(256, dtype='uint8')
        magenta[2] = np.arange(256, dtype='uint8')
        
        parent_folder_path = '/Users/domchom/Documents/GitHub/Bruker_to_ImageJ/tests/test_data/olympus'
        # parent_folder_path = '/Users/domchom/Documents/GitHub/Bruker_to_ImageJ/tests/test_data/bruker'
        avg_projection = False
        max_projection = False
        single_plane = False
        ch1_lut = red
        ch2_lut = green
        ch3_lut = blue
        ch4_lut = magenta
        microscope_type = 'Olympus' # 'Flamingo' or 'Bruker'
        auto_metadata_extract = True
        
    # Performance tracker
    start_time = timeit.default_timer()

    # Check if neither max nor avg projection are selected, default to saving full hyperstacks
    if not avg_projection and not max_projection:
        print('Neither max nor avg projection selected. Saving full hyperstacks. This might take a while!')
        projection_type = None
    elif max_projection:
        print('Max projection selected. Saving max projections.')
        projection_type = 'max'
    elif avg_projection:
        print('Avg projection selected. Saving avg projections.')
        projection_type = 'avg'
        
    # Create a dictionary of imagej metadata tags, with the LUTs for each channel. Will be used for all workflows.
    imagej_tags = createImageJMetadataTags(LUTs = {'LUTs': [ch1_lut, ch2_lut, ch3_lut, ch4_lut]},
                                           byteorder = '>')
    
    if microscope_type != 'Flamingo':
        # Get the Bruker image folders
        image_folders = sorted([folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))])
    
        # Initialize output folders, logging, and metadata CSV outout paths
        if not test:
            processed_images_path, scope_folders_path = initializeOutputFolders(parent_folder_path = parent_folder_path)
            metadata_csv_path = os.path.join(processed_images_path, "!image_metadata.csv")
        else:
            processed_images_path = parent_folder_path
            metadata_csv_path = None
        log_file_path, log_details = initializeLogFile(processed_images_path = processed_images_path)        
    
    # BRUKER WORKFLOW
    if microscope_type == 'Bruker':
        log_details = processBrukerImages(parent_folder_path = parent_folder_path,
                                           image_folders = image_folders,
                                           processed_images_path = processed_images_path,
                                           metadata_csv_path = metadata_csv_path,
                                           microscope_type = microscope_type,
                                           projection_type = projection_type,
                                           single_plane = single_plane,
                                           auto_metadata_extract = auto_metadata_extract,
                                           test = test,
                                           imagej_tags = imagej_tags,
                                           log_details = log_details
                                           )
                                          
            
    # OLYMPUS WORKFLOW
    elif microscope_type == 'Olympus':
        processOlympusImages(parent_folder_path=parent_folder_path,
                            processed_images_path=processed_images_path,
                            microscope_type=microscope_type,
                            projection_type=projection_type,
                            imagej_tags=imagej_tags,
                            image_folders=image_folders
                            )
                                    
    # FLAMINGO WORKFLOW
    elif microscope_type == 'Flamingo':
        # Get the list of all TIF files in the directory
        tif_filenames = [f for f in os.listdir(parent_folder_path) if f.endswith('.tif') and f.startswith('S')]
        # for reference filename structure: S000_t000000_V000_R0000_X000_Y000_C00_I0_D0_P00366
        # S: unsure, t: time point, V: unsure, R: rotation, X: x position, 
        # Y: y position, C: channel, I: illumination side, D: unsure, P: Z-planes

        # Get the number of channels and frames
        num_channels, channel_names = getNumChannelsFlamingo(tif_filenames)
        num_frames = getNumFramesFlamingo(tif_filenames)
        num_illumination_sides = getNumIlluminationSidesFlamingo(tif_filenames)
        print(f"Number of channels: {num_channels}")
        print(f"Number of frames: {num_frames}")
        print(f"Number of illumination sides: {num_illumination_sides}")

        # Read all TIF files and Z-project them (if desired)
        image_arrays = convertImagesToNumpyArraysAndProjectFlamingo(parent_folder_path, tif_filenames, projection_type)

        # Create the final hyperstack that will hold all frames
        final_hyperstack = mergeNumpyArrayIlluminationSidesFlamingo(image_arrays, 
                                                                tif_filenames, 
                                                                num_frames, 
                                                                num_channels, 
                                                                channel_names, 
                                                                projection_type
                                                                )

        # Create output path for the final hyperstack
        image_folder = os.path.basename(parent_folder_path)
        name_suffix = 'MAX' if projection_type == 'max' else 'AVG' if projection_type == 'avg' else 'hyperstack'
        hyperstack_output_path = f'{parent_folder_path}/{image_folder}_{name_suffix}.tif'
        
        # Check if the output file already exists
        if os.path.exists(hyperstack_output_path):
            print(f"Output file {hyperstack_output_path} already exists. Overwriting...")
            # Remove the existing file
            os.remove(hyperstack_output_path)
        
        # Create axes metadata for the hyperstack
        imageJ_axes = 'TCYX' if projection_type == 'max' or projection_type == 'avg' else 'TZCYX'
            
        # Calculate the size of the final hyperstack in bytes, and warn if it's too large
        # 1 GB = 1024^3 bytes
        final_hyperstack_size = final_hyperstack.nbytes
        if final_hyperstack_size > (1024 ** 3):
            print(f"Warning: The final hyperstack is {final_hyperstack_size / (1024 ** 3):.2f} GB. It may take a while to save.")
            print("Consider splitting the data into smaller chunks.")
            
        print(f"Saving hyperstack to {hyperstack_output_path}...")
        
        # Save the hyperstack
        saveImageJHyperstack(final_hyperstack, 
                        imageJ_axes,
                        metadata = None, # for now, flamingo data doesn't have metadata
                        image_output_name = hyperstack_output_path, 
                        imagej_tags = imagej_tags
                        ) 

        print(f'Successfully saved hyperstack to {hyperstack_output_path}')
          
    if microscope_type != 'Flamingo' and test == False: # not doing olympus for testing for now  
        for folder_name in image_folders:
            shutil.move(os.path.join(parent_folder_path, folder_name), os.path.join(scope_folders_path, folder_name))

            end_time = timeit.default_timer()
            log_details["Time Elapsed"] = f"{end_time - start_time:.2f} seconds"
            
            # Save the log file
            saveLogFile(log_file_path, log_details)    
    
    end_time = timeit.default_timer()
    print(f'Time elapsed: {end_time - start_time:.2f} seconds')    
              
if __name__ == '__main__':
    main()

print('Done with script!')
