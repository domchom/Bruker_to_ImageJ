import os
import timeit
import tifffile
from tqdm import tqdm
from functions import get_pixel_size, get_frame_rate, make_log, create_hyperstack

parent_folder_path = '/Volumes/T7/200DCE_240228_3xGFP-Ect2PH(PBC)_SFC/scope_folders'

# performance tracker
start = timeit.default_timer()

# get the folders
folders = [folder for folder in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, folder))]
folders = sorted(folders)

# create the output folder
output_path = os.path.join(parent_folder_path, "!processed_images")
os.makedirs(output_path, exist_ok=True)

# log file
log_params = {'Files Not Processed': [],
              'Files Processed': []}

with tqdm(total = len(folders)) as pbar:
    pbar.set_description('Files processed:')
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
                X_microns_per_pixel, Y_microns_per_pixel =  get_pixel_size(xml_file)

                # get the frame rate
                framerate = get_frame_rate(xml_file)

                # create the hyperstack
                hyperstack = create_hyperstack(folder_path)
                
                # save the hyperstack
                tifffile.imsave(
                    image_name, 
                    hyperstack,
                    imagej=True,
                    resolution=(1/X_microns_per_pixel, 1/Y_microns_per_pixel),
                    metadata={'axes': 'TCYX',
                            'finterval': framerate,
                            'mode': 'composite'}
                    )

                log_params['Files Processed'].append(folder)
                print(f"Successfully processed {folder}!")
            
        except Exception as e:
            log_params['Files Not Processed'].append(f'{folder}: {e}')
            pass

        pbar.update(1)
    
end = timeit.default_timer()
log_params["Time Elapsed"] = f"{end - start:.2f} seconds"

make_log(parent_folder_path, log_params)

print("Done!")
