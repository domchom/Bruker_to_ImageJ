import tqdm
import tifffile
import numpy as np

def getNumChannelsFlamingo(file_list: list) -> tuple:
    """
    Extract the number of channels from the filenames.
    The filenames are expected to contain channel information in the format 'C<number>'.
    
    Parameters
    file_list : list
        List of filenames to extract channel information from.
        
    Returns
    tuple
        A tuple containing the number of unique channels and a list of unique channel numbers.
    """
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

def getNumFramesFlamingo(file_list: list) -> int:
    """
    Extract the number of frames from the filenames.
    The filenames are expected to contain frame information in the format 'T<number>'.
    
    Parameters
    file_list : list
        List of filenames to extract frame information from.
        
    Returns
    int
        The number of unique frames.
    """
    # Extract the frame number from the filenames
    frame_numbers = set()
    for file in file_list:
        parts = file.split('_')
        for part in parts:
            if part.startswith('t') and part[1:].isdigit():
                frame_numbers.add(int(part[1:]))
                break

    return len(frame_numbers)

def getNumZPlanesFlamingo(file_list: list) -> int:
    """
    Extract the number of z planes from the filenames.
    The filenames are expected to contain frame information in the format 'P<number>'.
    
    Parameters
    file_list : list
        List of filenames to extract frame information from.
        
    Returns
    int
        The number of unique z planes.
    """
    # Extract the Z-plane number from the filenames
    for file in file_list:
        file = file.split('.')[0]
        parts = file.split('_')
        for part in parts:
            if part.startswith('P') and part[1:].isdigit():
                num_z_planes = int(part[1:])
                break

    return num_z_planes

def getNumIlluminationSidesFlamingo(file_list: list) -> int:
    """
    Extract the number of illumination sides from the filenames.
    The filenames are expected to contain illumination side information in the format 'I<number>'.
    
    Parameters
    file_list : list
        List of filenames to extract illumination side information from.
        
    Returns
    int
        The number of unique illumination sides.
    """
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

def convertImagesToNumpyArraysAndProjectFlamingo(folder_path: str, 
                            tif_files: list, 
                            projection_type: str = 'max',
                            ) -> list:
    """
    Convert TIFF images to numpy arrays and apply a z-projection.
    
    Parameters
    folder_path : str
        Path to the folder containing the TIFF files.
    tif_files : list
        List of TIFF filenames to be converted.
    projection_type : str
        Type of projection to apply ('max', 'avg', or 'sum').
        
    Returns
    list
        List of numpy arrays representing the images.
    """
    all_images = []

    for file_path in tqdm.tqdm(tif_files, desc="Reading files"):
        image_path = f'{folder_path}/{file_path}'  
        # Read the image
        image_array = tifffile.imread(image_path)
        # Z-projection here to reduce the 3D image to 2D and save memory
        if projection_type == 'max':
            image_array = zProject(image_array, projection_type='max')
        elif projection_type == 'avg':
            image_array = zProject(image_array, projection_type='avg')

        all_images.append(image_array)
    
    return all_images

def zProject(image: np.array,
              projection_type: str ='max' #default is max projection
              ) -> np.array:
    """
    Apply a z-projection to the image.
    
    Parameters
    image : np.array
        The image to be projected.
    projection_type : str
        Type of projection to apply ('max', 'avg', or 'sum').
        
    Returns
    np.array
        The projected image.
    """
    if projection_type == 'max':
        return np.max(image, axis=0)
    elif projection_type == 'avg':
        return np.mean(image, axis=0)
    else:
        raise ValueError("Invalid projection type. Choose 'max', 'avg', or 'sum'.")

def mergeNumpyArrayIlluminationSidesFlamingo(images: list,
                               filenames: list,
                               num_frames: int,
                               num_channels: int,
                               channels: list,
                               projection: str = 'max',
                               ) -> np.array:
    """
    Merge images from different illumination sides into a single hyperstack.
    
    Parameters
    images : list
        List of images to be merged.
    filenames : list
        List of filenames corresponding to the images.
    num_frames : int
        Number of frames in the images.
    num_channels : int
        Number of channels in the images.
    channels : list
        List of channel numbers.
    projection : str
        Type of projection to apply ('max', 'avg', or 'sum').  
    
    Returns
    np.array
        The merged hyperstack.
    """
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
        if projection == None:
            hyperstack = np.moveaxis(hyperstack, 1, 2) 
            hyperstack = np.moveaxis(hyperstack, 0, 1)  
        
        final_hyperstack.append(hyperstack)

    return np.stack(final_hyperstack, axis=0)