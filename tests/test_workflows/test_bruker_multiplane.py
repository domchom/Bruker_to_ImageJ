import os
import pytest
import numpy as np
import pandas as pd
from domilyzer.workflows.bruker_workflow import processBrukerImages

from domilyzer.functions_gui.general_functions import createImageJMetadataTags

@pytest.fixture
def default_parameters():
    folder_path = 'tests/test_data/bruker_multiplane'
    image_folders = sorted([
        folder for folder in os.listdir(folder_path)
        if os.path.isdir(os.path.join(folder_path, folder))
    ])
    
    red = np.zeros((3, 256), dtype='uint8')
    red[0] = np.arange(256, dtype='uint8')

    green = np.zeros((3, 256), dtype='uint8')
    green[1] = np.arange(256, dtype='uint8')

    blue = np.zeros((3, 256), dtype='uint8')
    blue[2] = np.arange(256, dtype='uint8')

    magenta = np.zeros((3, 256), dtype='uint8')
    magenta[0] = np.arange(256, dtype='uint8')
    magenta[2] = np.arange(256, dtype='uint8')
    
    return {
        'folder_path': 'tests/test_data/bruker_multiplane',
        'image_folders':image_folders,
        'projection_type': None,
        'single_plane': False,
        'microscope_type': 'Bruker',
        'auto_metadata_extract': True,
        'test': True,
        'metadata_csv_path': None,
        'imagej_tags': createImageJMetadataTags(LUTs = {'LUTs': [red, green, blue, magenta]},
                                           byteorder = '>'),
        'log_details': {
                    'Files Not Processed': [],
                   'Files Processed': [],
                   'Issues': [],
                   'Other Notes': []
                   }
        }

def test_bruker_multiplane_workflow(default_parameters):
    loaded_arrays = np.load('tests/assets/bruker_multiplane_hyperstack_arrays.npz')
    known_arrays = [loaded_arrays[f'array_{i}'] for i in range(len(loaded_arrays.files))]
    
    log_details, list_of_arrays = processBrukerImages(parent_folder_path=default_parameters['folder_path'],
                                                         image_folders=default_parameters['image_folders'],
                                                         processed_images_path='none',
                                                         metadata_csv_path=default_parameters['metadata_csv_path'],
                                                         microscope_type=default_parameters['microscope_type'],
                                                         projection_type=default_parameters['projection_type'],
                                                         single_plane=default_parameters['single_plane'],
                                                         auto_metadata_extract=default_parameters['auto_metadata_extract'],
                                                         test=default_parameters['test'],
                                                         imagej_tags=default_parameters['imagej_tags'],
                                                         log_details=default_parameters['log_details']
                                                         )
    
    for i, (arr1, arr2) in enumerate(zip(list_of_arrays, known_arrays)):
        assert np.array_equal(arr1, arr2), f"Arrays at index {i} differ"