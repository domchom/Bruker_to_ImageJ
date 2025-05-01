import os
import struct
import tifffile

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

def save_log_file(
    logPath: str, 
    logParams: dict
):
    '''
    Creates a log file in the specified directory with the specified parameters.

    Parameters
    directory : str
        The directory in which to create the log file.
    logParams : dict
        A dictionary containing the parameters to be logged.
    '''
    logFile = open(logPath, "w")                                    
    for key, value in logParams.items():                            
        logFile.write('%s: %s\n' % (key, value))                    
    logFile.close()   
    
def determine_scope(
    folder_path: str
):
    if '.oif' in folder_path:
        return 'Olympus'
    else:
        return 'Bruker'
    
def save_hyperstack(hyperstack, axes, metadata, image_output_name, imagej_tags):   
    # Write the hyperstack to a TIFF file
    if metadata == None: # for the flamingo data for now
        saved_metadata = {
            'axes': axes,
            'unit': 'um',
            'mode': 'composite'
        }
    else:  # for the bruker data for now
        saved_metadata = {
            'axes': axes,
            'finterval': metadata['framerate'], 
            'unit': 'um',
            'mode': 'composite'
        }
    tifffile.imwrite(image_output_name, 
                    hyperstack, 
                    byteorder='>', 
                    imagej=True,
                    resolution=(1 / metadata['X_microns_per_pixel'], 1 / metadata['Y_microns_per_pixel']),
                    metadata=saved_metadata, 
                    extratags=imagej_tags
                )
    

def imagej_metadata_tags(metadata, byteorder):
    """Return IJMetadata and IJMetadataByteCounts tags from metadata dict.

    The tags can be passed to the TiffWriter.save function as extratags.

    """
    header = [{'>': b'IJIJ', '<': b'JIJI'}[byteorder]]
    bytecounts = [0]
    body = []

    def writestring(data, byteorder):
        return data.encode('utf-16' + {'>': 'be', '<': 'le'}[byteorder])

    def writedoubles(data, byteorder):
        return struct.pack(byteorder+('d' * len(data)), *data)

    def writebytes(data, byteorder):
        return data.tobytes()

    metadata_types = (
        ('Info', b'info', 1, writestring),
        ('Labels', b'labl', None, writestring),
        ('Ranges', b'rang', 1, writedoubles),
        ('LUTs', b'luts', None, writebytes),
        ('Plot', b'plot', 1, writebytes),
        ('ROI', b'roi ', 1, writebytes),
        ('Overlays', b'over', None, writebytes))

    for key, mtype, count, func in metadata_types:
        if key not in metadata:
            continue
        if byteorder == '<':
            mtype = mtype[::-1]
        values = metadata[key]
        if count is None:
            count = len(values)
        else:
            values = [values]
        header.append(mtype + struct.pack(byteorder+'I', count))
        for value in values:
            data = func(value, byteorder)
            body.append(data)
            bytecounts.append(len(data))

    body = b''.join(body)
    header = b''.join(header)
    data = header + body
    bytecounts[0] = len(header)
    bytecounts = struct.pack(byteorder+('I' * len(bytecounts)), *bytecounts)
    return ((50839, 'B', len(data), data, True),
            (50838, 'I', len(bytecounts)//4, bytecounts, True))
