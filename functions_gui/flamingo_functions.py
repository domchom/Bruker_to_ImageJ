import tqdm
import tifffile
import numpy as np

def get_num_channels_flamingo(file_list):
    # Extract the channel number from the filenames
    channel_numbers = []
    for file in file_list:
        parts = file.split('_')
        for part in parts:
            if part.startswith('C') and part[1:].isdigit():
                if part[1:] not in channel_numbers:
                    channel_numbers.append(part[1:])
                break

    return len(channel_numbers), channel_numbers

def get_num_frames_flamingo(file_list):
    # Extract the frame number from the filenames
    frame_numbers = []
    for file in file_list:
        parts = file.split('_')
        for part in parts:
            if part.startswith('t') and part[1:].isdigit():
                if int(part[1:]) not in frame_numbers:
                    frame_numbers.append(int(part[1:]))
                break

    return len(frame_numbers)

def get_num_z_planes_flamingo(file_list):
    # Extract the Z-plane number from the filenames
    for file in file_list:
        file = file.split('.')[0]
        parts = file.split('_')
        for part in parts:
            if part.startswith('P') and part[1:].isdigit():
                num_z_planes = int(part[1:])
                break

    return num_z_planes

def get_num_illumination_sides_flamingo(file_list):
    # Extract the excitation side from the filenames
    excite_sides = []
    for file in file_list:
        parts = file.split('_')
        for part in parts:
            if part.startswith('I') and part[1:].isdigit():
                if int(part[1:]) not in excite_sides:
                    excite_sides.append(int(part[1:]))
                break

    return len(excite_sides)

def get_all_img_filenames_flamingo(file_list):
    # Extract the image filenames from the list
    img_filenames = []
    for file in file_list:
        parts = file.split('_')
        for part in parts:
            if part.startswith('I') and part[1:].isdigit():
                img_filenames.append(file)
                break

    return img_filenames

def process_flamingo_folder(folder_path: str, 
                            tif_files: list, 
                            max_projection: bool = False, 
                            avg_projection: bool = False
                            ) -> list:
    all_images = []

    for file_path in tqdm.tqdm(tif_files, desc="Reading files"):
        image_path = f'{folder_path}/{file_path}'  
        # Read the image
        image = tifffile.imread(image_path)
        # Z-projection here to reduce the 3D image to 2D and save memory
        if max_projection:
            image = Z_project_flamingo(image, projection_type='max')
        elif avg_projection:
            image = Z_project_flamingo(image, projection_type='avg')

        all_images.append(image)
    
    return all_images

def Z_project_flamingo(image: np.array,
              projection_type: str ='max' #default is max projection
              ) -> np.array:
    if projection_type == 'max':
        return np.max(image, axis=0)
    elif projection_type == 'avg':
        return np.mean(image, axis=0)
    else:
        raise ValueError("Invalid projection type. Choose 'max', 'avg', or 'sum'.")

def combine_illumination_sides_flamingo(images: list,
                               filenames: list,
                               num_frames: int,
                               num_channels: int,
                               channels: list,
                               max_projection: bool = False,
                               avg_projection: bool = False   
                               ) -> np.array:
    final_hyperstack = []

    for frame in tqdm.tqdm(range(num_frames), desc="Processing frames"):
        # Filter images for the current frame
        frame_filter = f't{frame:06d}'
        frame_images = []
        for channel in range(num_channels):
            # Filter images for the current frame and channel
            channel_filter = f'C{channels[channel]}'
            channel_images = [img for img, file in zip(images, filenames) if frame_filter in file and channel_filter in file]
            
            # Combine all images by taking the max pixel value across all illumination sides
            combined_image = np.max(channel_images, axis=0)
            # Rotate the combined image 90 degrees counterclockwise
            rotated_image = np.rot90(combined_image)
            frame_images.append(rotated_image)

        # Stack the two channels into a hyperstack, and add to the final hyperstack
        hyperstack = np.stack(frame_images, axis=0)
        if not max_projection and not avg_projection:
            hyperstack = np.moveaxis(hyperstack, 1, 2) 
            hyperstack = np.moveaxis(hyperstack, 0, 1)  
        
        final_hyperstack.append(hyperstack)

    return np.stack(final_hyperstack, axis=0)