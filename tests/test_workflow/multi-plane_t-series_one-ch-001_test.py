import pytest
import pandas as pd
from functions_gui import process_folder

@pytest.fixture
def default_parameters():
    return {
        'folder_path': '/Users/domchom/Documents/GitHub/Bruker_to_ImageJ/tests/test_data/multi-plane_t-series_one-ch-001',
        'max_project': True,
        'single_plane': False,
        }

def test_standard_workflow(default_parameters):
    known_results = pd.read_csv('tests/assets/standard/known_standard_summary.csv')
    # process the folder
    exp_results = process_folder(folder_name = None,
                                parent_folder_path = None, 
                                processed_images_path = None, 
                                imagej_tags = None, 
                                max_projection = True, 
                                log_details = None, 
                                metadata_csv_path = None,
                                single_plane=False,
                                test = True)
                    # compare the results
    assert pd.testing.assert_frame_equal(known_results, exp_results) is None

    ### THE ABOVE IS DEFINITELY NOT CORRECT, BUT I'M NOT SURE HOW TO FIX IT ###