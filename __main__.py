import os
import timeit
import shutil
import tifffile
from functions_gui.gui import BaseGUI, FlamingoGUI
from functions_gui.bruker_functions import (
    save_log_file, 
    determine_scope, 
    imagej_metadata_tags, 
    initialize_output_folders,
    setup_logging,
    extract_metadata,
    create_hyperstack,
    save_hyperstack,
    write_metadata_csv,
    determine_axes
    
)
from functions_gui.flamingo_functions import (
    get_num_channels,
    get_num_frames,
    get_num_illumination_sides,
    process_flamingo_folder,
    combine_illumination_sides
)

def main():
    # Bruker GUI
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
    
    # If user specifies Flamingo data
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
    
    # Check if both max and avg projection are selected, default to max projection if both are
    if avg_projection and max_projection:
            print('Both max and avg projection selected. Only max projection will be used.')
            avg_projection = False
    # Check if neither max nor avg projection are selected
    if not avg_projection and not max_projection:
        print('Neither max nor avg projection selected. Saving full hyperstacks. This might take a while!')
        
    # Create a dictionary of imagej metadata tags
    imagej_tags = imagej_metadata_tags({'LUTs': [ch1_lut, ch2_lut, ch3_lut, ch4_lut]}, '>')
    
    # Determine the microscope type # TODO: need to fully implement this function once olympus function is finished
    microscope_type = determine_scope(image_folders[0])

    # If Bruker data
    if not flamingo:
        # Get the Bruker image folders
        image_folders = sorted([folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))])

        # Initialize output folders, logging, and metadata CSV outout paths
        processed_images_path, scope_folders_path = initialize_output_folders(parent_folder_path)
        log_file_path, log_details = setup_logging(processed_images_path)
        metadata_csv_path = os.path.join(processed_images_path, "!image_metadata.csv")

        for folder_name in image_folders:
            print('******'*10)
            try:
                # Check for XML file and extract relevant metadata
                folder_path = os.path.join(parent_folder_path, folder_name)
                xml_files = [file for file in os.listdir(folder_path) if os.path.splitext(file)[1] == ".xml"]   
                if not xml_files:
                    raise FileNotFoundError(f"No XML file found in folder {folder_name}")
                else:
                    xml_file_path = os.path.join(folder_path, xml_files[0])
                    extracted_metadata = extract_metadata(xml_file_path, log_details)
                    
                # Create the hyperstack and get the image type
                hyperstack, image_type = create_hyperstack(folder_path, avg_projection, max_projection, single_plane)
                
                # Recalculate the frame rate for single plane: divide by number of frames
                frame_rate = frame_rate / hyperstack.shape[0] if 'single_plane' in image_type else frame_rate
                
                # create the output image name
                prefix = "MAX_" if "max_project" in image_type else "AVG_" if "avg_project" in image_type else ""
                image_output_name = os.path.join(processed_images_path, f"{prefix}{folder_name}_raw.tif")
                if os.path.exists(image_output_name):
                    print(f"{folder_name} already exists!")
                    log_details['Files Not Processed'].append(f'{folder_name}: Already exists!')
                    return log_details
                
                # determine the axes for the hyperstack
                axes = determine_axes(image_type)
                
                # Save the hyperstack
                save_hyperstack(hyperstack, axes, extracted_metadata, image_output_name, imagej_tags)
                
                # Create metadata for the hyperstack, and update the log file to save after all folders are processed
                log_details = write_metadata_csv(metadata, metadata_csv_path, folder_name, log_details)
                    
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
        save_log_file(log_file_path, log_details)
    
    # If Flamingo data
    else:
        # Get the list of all TIF files in the directory
        tif_files = [f for f in os.listdir(parent_folder_path) if f.endswith('.tif') and f.startswith('S')]
        # for reference filename structure: S000_t000000_V000_R0000_X000_Y000_C00_I0_D0_P00366
        # S: unsure, t: time point, V: unsure, R: rotation, X: x position, 
        # Y: y position, C: channel, I: illumination side, D: unsure, P: Z-planes

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
        final_hyperstack = combine_illumination_sides(all_images, 
                                                      tif_files, 
                                                      num_frames, 
                                                      num_channels, 
                                                      channels, 
                                                      max_projection, 
                                                      avg_projection)

        # Create output path for the final hyperstack
        folder_name = os.path.basename(parent_folder_path)
        name_suffix = 'MAX' if max_projection else 'AVG' if avg_projection else 'hyperstack'
        hyperstack_output_path = f'{parent_folder_path}/{folder_name}_{name_suffix}.tif'
        
        # Check if the output file already exists
        if os.path.exists(hyperstack_output_path):
            print(f"Output file {hyperstack_output_path} already exists. Overwriting...")
            # Remove the existing file
            os.remove(hyperstack_output_path)
        
        # Create metadata for the hyperstack
        if max_projection == True or avg_projection == True: 
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
         
        # Calculate the size of the final hyperstack in bytes, and warn if it's too large
        # 1 GB = 1024^3 bytes
        final_hyperstack_size = final_hyperstack.nbytes
        if final_hyperstack_size > (1024 ** 3):
            print(f"Warning: The final hyperstack is {final_hyperstack_size / (1024 ** 3):.2f} GB. It may take a while to save.")
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
        
        end_time = timeit.default_timer()
        print(f'Time elapsed: {end_time - start_time:.2f} seconds')
                            
if __name__ == '__main__':
    main()

print('Done with script!')
