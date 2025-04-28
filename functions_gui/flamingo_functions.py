import numpy as np

def get_num_channels(file_list):
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

def get_num_frames(file_list):
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

def get_num_z_planes(file_list):
    # Extract the Z-plane number from the filenames
    for file in file_list:
        file = file.split('.')[0]
        parts = file.split('_')
        for part in parts:
            if part.startswith('P') and part[1:].isdigit():
                num_z_planes = int(part[1:])
                break

    return num_z_planes

def get_num_illumination_sides(file_list):
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

def get_all_img_filenames(file_list):
    # Extract the image filenames from the list
    img_filenames = []
    for file in file_list:
        parts = file.split('_')
        for part in parts:
            if part.startswith('I') and part[1:].isdigit():
                img_filenames.append(file)
                break

    return img_filenames

def Z_project(image, projection_type='max'):
    if projection_type == 'max':
        return np.max(image, axis=0)
    elif projection_type == 'avg':
        return np.mean(image, axis=0)
    elif projection_type == 'sum':
        return np.sum(image, axis=0)
    else:
        raise ValueError("Invalid projection type. Choose 'max', 'avg', or 'sum'.")
