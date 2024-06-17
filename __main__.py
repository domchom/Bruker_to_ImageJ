import os
import csv
import timeit
import shutil
import tifffile
import numpy as np
from functions_gui.gui import BaseGUI
from functions_gui.functions import get_pixel_size, get_frame_rate, make_log, create_hyperstack, extract_metadata, determine_scope, create_hyperstack_olympus, imagej_metadata_tags

# TODO: make it so that the user does not need to install any packages manually

# just for testing. No need to use this if you plan to use the GUI
parent_folder_path = '/Volumes/T7/!Rho-IT/212DCE_240522_mCh-IT-Rho_GFP-rGBD_SFC'

def main():
    gui = BaseGUI()
    gui.mainloop()

    # get GUI variables
    parent_folder_path = gui.folder_path
    max_project = gui.max_project
    ch1_lut = gui.channel1_var
    ch2_lut = gui.channel2_var
    ch3_lut = gui.channel3_var
    ch4_lut = gui.channel4_var

    # create the imagej tags to load the LUTs
    ijtags = imagej_metadata_tags({'LUTs': [ch1_lut, ch2_lut, ch3_lut, ch4_lut]}, '>')

    # performance tracker
    start = timeit.default_timer()

    # get the Bruker image folders
    folders = [folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))]
    folders = sorted(folders)

    # create the output folder
    output_path = os.path.join(parent_folder_path, "!processed_images")
    os.makedirs(output_path, exist_ok=True)

    # create output folder to put the microscope folders after conversion
    scope_folders_path = os.path.join(parent_folder_path, "!scope_folders")
    os.makedirs(scope_folders_path, exist_ok=True)

    # set log file path and parameters
    logPath = os.path.join(output_path, f"!image_conversion_log.txt")
    log_params = {'Files Not Processed': [],
                'Files Processed': [],
                'Issues': []}

    # determine the microscope type 
    microscope_type = determine_scope(folders[0])

    if microscope_type == 'Bruker':
        print('Bruker microscope detected!')
        
        # create the csv file to store the metadata
        csv_file_path = os.path.join(output_path, "!image_metadata.csv")
        with open(csv_file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Folder Name', 
                            'Pixel Size', 
                            'Z depth', 
                            'Frame Rate',
                            'Bit Depth', 
                            'Dwell Time', 
                            'Helios ND Filter Values', 
                            'Laser Power Values', 
                            'Objective Lens Description'])    

        for folder in folders:
            print('******'*10)
            try:
                # set the folder_path and image name
                folder_path = os.path.join(parent_folder_path, folder)

                # get the xml file and extract the pixel size and frame rate
                xml_file = [file for file in os.listdir(folder_path) if os.path.splitext(file)[1] == ".xml"]
                xml_file = os.path.join(folder_path, xml_file[0])
                X_microns_per_pixel, Y_microns_per_pixel, Z_microns_per_pixel =  get_pixel_size(xml_file)
                framerate = get_frame_rate(xml_file)

                # create the hyperstack
                hyperstack, image_type = create_hyperstack(folder_path, max_project)

                # workflow to save max projected multi-plane images
                if image_type == 'multi_plane_multi_timepoint_max_project' or image_type == 'multi_plane_single_timepoint_max_project':
                    image_name = os.path.join(output_path, f"MAX_{folder}_raw.tif")
                    if os.path.exists(image_name):
                        print(f"{folder} already exists!")
                        log_params['Files Not Processed'].append(f'{folder}: Already exists!')
                        pass
                    else:
                        tifffile.imwrite(
                            image_name, 
                            hyperstack,
                            byteorder='>',
                            imagej=True,
                            resolution=(1/X_microns_per_pixel, 1/Y_microns_per_pixel),
                            metadata={'axes': 'TCYX',
                                    'finterval': framerate,
                                    'mode': 'composite'
                                    },
                            extratags=ijtags
                            )
                                        
                # workflow to save multi-plane images as hyperstack, and single plane images
                if image_type == 'multi_plane_multi_timepoint' or image_type == 'multi_plane_single_timepoint' or image_type == 'single_plane':
                    if image_type == 'single_plane':
                        # Have to recalculate the framerate for single plane
                        num_frames = hyperstack.shape[0]
                        framerate = framerate / num_frames
                    image_name = os.path.join(output_path, f"{folder}_raw.tif")
                    if os.path.exists(image_name):
                        print(f"{folder} already exists!")
                        log_params['Files Not Processed'].append(f'{folder}: Already exists!')
                        pass
                    else:
                        tifffile.imwrite(
                            image_name, 
                            hyperstack,
                            byteorder='>',
                            imagej=True,
                            resolution=(1/X_microns_per_pixel, 1/Y_microns_per_pixel),
                            metadata={'axes': 'TZCYX',
                                    'finterval': framerate,
                                    'mode': 'composite'
                                    },
                            extratags=ijtags
                            )              
        
                # extract the metadata and save it in the csv file
                bit_depth, dwell_time, helios_nd_filter_values, laser_power_values, objective_lens_description, log_params = extract_metadata(xml_file, log_params)
                with open(csv_file_path, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([folder, 
                                    X_microns_per_pixel, 
                                    Z_microns_per_pixel,
                                    framerate, 
                                    bit_depth, 
                                    dwell_time,
                                    helios_nd_filter_values, 
                                    laser_power_values, 
                                    objective_lens_description])  

                log_params['Files Processed'].append(folder)
                print(f"Successfully processed {folder}!")
                    
            except Exception as e:
                log_params['Files Not Processed'].append(f'{folder}: {e}' )
                print(f"Error processing {folder}!")
                pass
            
        end = timeit.default_timer()
        log_params["Time Elapsed"] = f"{end - start:.2f} seconds"

        make_log(logPath, log_params)

        # Move original folders to scope_folders after conversion
        for folder in folders:
            original_folder_path = os.path.join(parent_folder_path, folder)
            new_folder_path = os.path.join(scope_folders_path, folder)
            shutil.move(original_folder_path, new_folder_path)

    else:
        # TODO: finish Olympus microscope conversion
        print('Olympus microscope detected!')
        
        files_in_folder = [os.path.join(parent_folder_path, file) for file in os.listdir(parent_folder_path)]

        for file in files_in_folder:
            image = create_hyperstack_olympus(file)       
           
if __name__ == '__main__':
    main()

print('Done with script!')
