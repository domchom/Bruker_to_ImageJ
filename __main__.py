import os
import csv
import timeit
import shutil
import tifffile
from functions_gui.gui import BaseGUI
from functions_gui.functions import (
    make_log, create_hyperstack, extract_metadata, 
    determine_scope, create_hyperstack_olympus, imagej_metadata_tags
)

def initialize_output_folders(parent_folder_path) -> tuple:
    '''
    Create the output folders for the processed images and the scope folders.
    '''
    processed_images_path = os.path.join(parent_folder_path, "!processed_images")
    os.makedirs(processed_images_path, exist_ok=True)
    scope_folders_path = os.path.join(parent_folder_path, "!scope_folders")
    os.makedirs(scope_folders_path, exist_ok=True)
    return processed_images_path, scope_folders_path

def setup_logging(processed_images_path) -> tuple:
    '''
    Set up the log file and parameters.
    '''
    log_file_path = os.path.join(processed_images_path, "!image_conversion_log.txt")
    log_details = {'Files Not Processed': [],
                   'Files Processed': [],
                   'Issues': []}
    return log_file_path, log_details

def process_folder(folder_name, 
                   parent_folder_path, 
                   processed_images_path, 
                   imagej_tags, 
                   max_projection, 
                   log_details, 
                   metadata_csv_path
                   ) -> dict:
    '''
    Process the folder and create the hyperstack. Also extract metadata and write to CSV.
    '''
    # Check for XML file and get relevant metadata
    folder_path = os.path.join(parent_folder_path, folder_name)
    xml_files = [file for file in os.listdir(folder_path) if os.path.splitext(file)[1] == ".xml"]   
    if not xml_files:
        raise FileNotFoundError(f"No XML file found in folder {folder_name}")
    else:
        xml_file_path = os.path.join(folder_path, xml_files[0])
        bit_depth, dwell_time, helios_nd_filter_values, laser_power_values, objective_lens_description, log_details, frame_rate, X_microns_per_pixel, Y_microns_per_pixel, Z_microns_per_pixel = extract_metadata(xml_file_path, log_details)

    # Create the hyperstack and get the image type
    hyperstack, image_type = create_hyperstack(folder_path, max_projection)

    # Recalculate the frame rate for single plane: divide by number of frames
    frame_rate = frame_rate / hyperstack.shape[0] if image_type == 'single_plane' else frame_rate
    
    # create the output image name
    image_output_name = os.path.join(processed_images_path, f"{'MAX_' if 'max_project' in image_type else ''}{folder_name}_raw.tif")
    if os.path.exists(image_output_name):
        print(f"{folder_name} already exists!")
        log_details['Files Not Processed'].append(f'{folder_name}: Already exists!')
        return log_details
    
    # Write the hyperstack to a TIFF file
    metadata = {
        'axes': 'TCYX' if 'max_project' in image_type else 'TZCYX',
        'finterval': frame_rate, 'unit': 'um',
        'mode': 'composite'
    }
    tifffile.imwrite(image_output_name, 
                    hyperstack, 
                    byteorder='>', 
                    imagej=True,
                    resolution=(1 / X_microns_per_pixel, 1 / Y_microns_per_pixel),
                    metadata=metadata, 
                    extratags=imagej_tags
                )
    
    # Prepare the column headers and values for laser power
    laser_power_headers = [f'{value.split(":")[-1].strip()} power' for value in laser_power_values.values()]
    laser_powers = [value.split(':')[1].split(',')[0].strip() for value in laser_power_values.values()]

    # Prepare the column headers and values for ND filters        
    nd_filter_headers = ['imaging light path', 'PA light path']
    nd_filter_values = [value.split(':')[-1].strip() for value in helios_nd_filter_values.values()]

    # Check if the file exists and create headers if not
    try:
        with open(metadata_csv_path, 'r') as file:
            existing_headers = file.readline().strip().split(',')
    except FileNotFoundError:
        existing_headers = []

    if not existing_headers:
        # Write the headers
        with open(metadata_csv_path, 'w', newline='') as file:
            csv_writer = csv.writer(file)
            headers = ["Folder Name", "X microns per pixel", "Z microns per pixel", 
                       "Frame Rate", "Bit Depth", "Dwell Time", 
                       "Objective Lens Description"] + laser_power_headers + nd_filter_headers
            csv_writer.writerow(headers)

    # Write metadata to CSV
    with open(metadata_csv_path, 'a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([folder_name, X_microns_per_pixel, Z_microns_per_pixel, frame_rate, 
                             bit_depth, dwell_time, objective_lens_description] + laser_powers + nd_filter_values)
    
    # Add folder name to log
    log_details['Files Processed'].append(folder_name)
    print(f"Successfully processed {folder_name}!")
    return log_details

def main():
    gui = BaseGUI()
    gui.mainloop()

    # Performance tracker
    start_time = timeit.default_timer()

    # Get GUI variables
    parent_folder_path = gui.folder_path
    max_projection = gui.max_project
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

    if microscope_type == 'Bruker':
        print('Bruker microscope detected!')
        
        for folder_name in image_folders:
            print('******'*10)
            try:
                log_details = process_folder(folder_name, parent_folder_path, processed_images_path, imagej_tags, max_projection, log_details, metadata_csv_path)
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
