import os
import timeit
import shutil
from functions_gui.gui import BaseGUI
from functions_gui.functions import (
    make_log, 
    determine_scope, 
    create_hyperstack_olympus, 
    imagej_metadata_tags, 
    process_folder, 
    initialize_output_folders,
    setup_logging
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

    # Create the ImageJ tags to load the LUTs
    imagej_tags = imagej_metadata_tags({'LUTs': [ch1_lut, ch2_lut, ch3_lut, ch4_lut]}, '>')

    # Get the Bruker image folders
    image_folders = sorted([folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))])

    # Initialize output folders, logging, and metadata CSV
    processed_images_path, scope_folders_path = initialize_output_folders(parent_folder_path)
    log_file_path, log_details = setup_logging(processed_images_path)
    metadata_csv_path = os.path.join(processed_images_path, "!image_metadata.csv")

    # Determine the microscope type 
    microscope_type = determine_scope(image_folders[0])

    if avg_projection and max_projection:
        print('Both max and avg projection selected. Only max projection will be used.')
        avg_projection = False
    if not avg_projection and not max_projection:
        print('Neither max nor avg projection selected. Defaulting to max projection.')
        max_projection = True

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
                
if __name__ == '__main__':
    main()

print('Done with script!')
