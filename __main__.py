import os
import csv
import timeit
import tifffile
from functions_gui.gui import BaseGUI
from functions_gui.functions import get_pixel_size, get_frame_rate, make_log, create_hyperstack, extract_metadata

# TODO: make it so that the user does not need to install any packages manually

# just for testing. No need to use this if you plan to use the GUI
parent_folder_path = '/Users/domchom/Desktop/test'

def main():
    gui = BaseGUI()
    gui.mainloop()

    # get standard GUI parameters
    parent_folder_path = gui.folder_path

    # performance tracker
    start = timeit.default_timer()

    # get the folders
    folders = [folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))]
    folders = sorted(folders)

    # create the output folder
    output_path = os.path.join(parent_folder_path, "!processed_images")
    os.makedirs(output_path, exist_ok=True)

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

    # set log file path and parameters
    logPath = os.path.join(output_path, f"!image_conversion_log.txt")
    log_params = {'Files Not Processed': [],
                'Files Processed': [],
                'Issues': []}

    for folder in folders:
        print('******'*10)
        try:
            # set the folder_path and image name
            folder_path = os.path.join(parent_folder_path, folder)
            image_name = os.path.join(output_path, f"MAX_{folder}_raw.tif")

            if os.path.exists(image_name):
                print(f"{folder} already exists!")
                log_params['Files Not Processed'].append(f'{folder}: Already exists!')

                pass

            else:
                # get the xml file
                xml_file = [file for file in os.listdir(folder_path) if os.path.splitext(file)[1] == ".xml"]
                xml_file = os.path.join(folder_path, xml_file[0])

                # get the pixel size
                X_microns_per_pixel, Y_microns_per_pixel, Z_microns_per_pixel =  get_pixel_size(xml_file)
                
                # get the frame rate
                framerate = get_frame_rate(xml_file)

                # create the hyperstack
                hyperstack, image_type = create_hyperstack(folder_path)
                                    
                if image_type == 'multi_plane_multi_timepoint':
                    tifffile.imwrite(
                        image_name, 
                        hyperstack,
                        imagej=True,
                        resolution=(1/X_microns_per_pixel, 1/Y_microns_per_pixel),
                        metadata={'axes': 'TCYX',
                                'finterval': framerate,
                                'mode': 'composite'}
                        )
                
                if image_type == 'multi_plane_single_timepoint':
                    tifffile.imwrite(
                        image_name, 
                        hyperstack,
                        imagej=True,
                        resolution=(1/X_microns_per_pixel, 1/Y_microns_per_pixel),
                        metadata={'axes': 'TZCYX',
                                'mode': 'composite'}
                        )
                
                if image_type == 'single_plane':
                    # Have to recalculate the framerate for single plane
                    num_frames = hyperstack.shape[0]
                    framerate = framerate / num_frames
                    tifffile.imwrite(
                        image_name, 
                        hyperstack,
                        imagej=True,
                        resolution=(1/X_microns_per_pixel, 1/Y_microns_per_pixel),
                        metadata={'axes': 'TZCYX',
                                'finterval': framerate,
                                'mode': 'composite'}
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
            log_params['Files Not Processed'].append(f'{folder}: {e}')
            pass
        
    end = timeit.default_timer()
    log_params["Time Elapsed"] = f"{end - start:.2f} seconds"

    make_log(logPath, log_params)

if __name__ == '__main__':
    main()

print('Done with script!')
