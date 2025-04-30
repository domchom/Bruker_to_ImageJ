import os
import timeit
import shutil
import tifffile
from functions_gui.gui import BaseGUI, FlamingoGUI
from functions_gui.functions import (
    make_log, 
    determine_scope, 
    create_hyperstack_olympus, 
    imagej_metadata_tags, 
    process_folder, 
    initialize_output_folders,
    setup_logging
)
from functions_gui.flamingo_functions import (
    get_num_channels,
    get_num_frames,
    get_num_illumination_sides,
    process_flamingo_folder,
    combine_illumination_sides
)


def main():
    gui = BaseGUI()
    gui.mainloop()

    # Performance tracker
    start_time = timeit.default_timer()

    # Get GUI variables
    parent_folder_path = gui.folder_path
    avg_projection = gui.avg_project
    max_projection = gui.max_project
    single_plane = gui.single_plane
    ch1_lut = gui.channel1_var
    ch2_lut = gui.channel2_var
    ch3_lut = gui.channel3_var
    ch4_lut = gui.channel4_var
    flamingo = gui.flamingo
    
    if gui.flamingo:
        gui = FlamingoGUI()
        gui.mainloop()
        
        # Performance tracker
        start_time = timeit.default_timer()

        # Get GUI variables
        parent_folder_path = gui.folder_path
        avg_projection = gui.avg_project
        max_projection = gui.max_project
        ch1_lut = gui.channel1_var
        ch2_lut = gui.channel2_var
        ch3_lut = gui.channel3_var
        ch4_lut = gui.channel4_var
        flamingo = gui.flamingo
    
    if avg_projection and max_projection:
            print('Both max and avg projection selected. Only max projection will be used.')
            avg_projection = False
    if not avg_projection and not max_projection:
        print('Neither max nor avg projection selected. Saving full hyperstacks. This might take a while!')
        
    # Create a dictionary of imagej metadata tags
    imagej_tags = imagej_metadata_tags({'LUTs': [ch1_lut, ch2_lut, ch3_lut, ch4_lut]}, '>')

    if not flamingo:
        # Get the Bruker image folders
        image_folders = sorted([folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))])

        # Initialize output folders, logging, and metadata CSV
        processed_images_path, scope_folders_path = initialize_output_folders(parent_folder_path)
        log_file_path, log_details = setup_logging(processed_images_path)
        metadata_csv_path = os.path.join(processed_images_path, "!image_metadata.csv")

        # Determine the microscope type 
        microscope_type = determine_scope(image_folders[0])

        if microscope_type == 'Bruker':
            print('Bruker microscope detected!')
            
            for folder_name in image_folders:
                print('******'*10)
                try:
                    log_details = process_folder(folder_name, parent_folder_path, processed_images_path, imagej_tags, avg_projection, max_projection, log_details, metadata_csv_path, single_plane)
                except Exception as e:
                    log_details['Files Not Processed'].append(f'{folder_name}: {e}')
                    print(f"Error processing {folder_name}!")
                    pass
                
        else:
            # TODO: Finish Olympus microscope conversion
            print('Olympus microscope detected! Olympus conversion is not yet implemented.')
            
            files_in_parent_folder = [os.path.join(parent_folder_path, file) for file in os.listdir(parent_folder_path)]

            for file_path in files_in_parent_folder:
                image = create_hyperstack_olympus(file_path)    

        for folder_name in image_folders:
            shutil.move(os.path.join(parent_folder_path, folder_name), os.path.join(scope_folders_path, folder_name))

        end_time = timeit.default_timer()
        log_details["Time Elapsed"] = f"{end_time - start_time:.2f} seconds"
        make_log(log_file_path, log_details)
    
    # If Flamingo data
    else:
        # Get the list of all TIF files in the directory
        tif_files = [f for f in os.listdir(parent_folder_path) if f.endswith('.tif') and f.startswith('S')]
        # for reference filename structure: S000_t000000_V000_R0000_X000_Y000_C00_I0_D0_P00366
        # S: unsure
        # t: time point
        # V: unsure
        # R: rotation
        # X: x position
        # Y: y position
        # C: channel
        # I: illumination side
        # D: unsure
        # P: number of Z-planes

        # Get the number of channels and frames
        num_channels, channels = get_num_channels(tif_files)
        num_frames = get_num_frames(tif_files)
        num_illumination_sides = get_num_illumination_sides(tif_files)
        print(f"Number of channels: {num_channels}")
        print(f"Number of frames: {num_frames}")
        print(f"Number of illumination sides: {num_illumination_sides}")

        # Read all TIF files and Z-project them (if desired)
        all_images = process_flamingo_folder(parent_folder_path, tif_files, max_projection, avg_projection)

        # Create the final hyperstack that will hold all frames
        final_hyperstack = combine_illumination_sides(all_images, tif_files, num_frames, num_channels, channels, max_projection, avg_projection)

        # Save the hyperstack as a multi-page TIFF
        folder_name = os.path.basename(parent_folder_path)
        name_suffix = 'MAX' if max_projection else 'AVG' if avg_projection else 'hyperstack'
        hyperstack_output_path = f'{parent_folder_path}/{folder_name}_{name_suffix}.tif'
        if max_projection or avg_projection: 
            metadata = {
                'axes': 'TCYX',
                'unit': 'um',
                'mode': 'composite'
            }
        else:
            metadata = {
                'axes': 'TZCYX',
                'unit': 'um',
                'mode': 'composite'
            }
         
        # Calculate the size of the final hyperstack in bytes
        final_hyperstack_size = final_hyperstack.nbytes
        print(f"Final hyperstack size: {final_hyperstack_size / (1024 ** 3):.2f} GB")
        if final_hyperstack_size > 2 * (1024 ** 3):
            print("Warning: The final hyperstack is larger than 2 GB. It may take a while to save.")
            print("Consider splitting the data into smaller chunks.")
            
        print(f"Saving hyperstack to {hyperstack_output_path}...")
        tifffile.imwrite(hyperstack_output_path, 
                            final_hyperstack, 
                            byteorder='>', 
                            imagej=True,
                            metadata=metadata,
                            extratags=imagej_tags
                        )

        print(f'Successfully saved hyperstack to {hyperstack_output_path}')

                            
if __name__ == '__main__':
    main()

print('Done with script!')
