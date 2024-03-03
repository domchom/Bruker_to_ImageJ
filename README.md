## Bruker to ImageJ Batch Import Workflow

This workflow is designed to batch import Bruker files into ImageJ formats. It also imports the frame rate and pixel size, assuming the correct objective is set.

### Compatibility

As of version 230229, this workflow is working for files saved on the SFC and confocal systems. Please note the following limitations:

- This workflow is designed for timeseries data and may not work with single z-stack images.
- The MIP (Maximum Intensity Projection) image should be saved already from the microscope.
- While this workflow should work with any number of channels, it has only been tested with 2-3 channels.

### Usage

To use this workflow, follow these steps:

1. Open the `main_workflow.py` file.
2. Use the GUI to select the parent folder containing the Bruker folders for individual movies.
2a. Alternatively, you click comment out the gui code and just copy and paste the path to the folder in the correct location.
3. Run the `main_workflow.py` script.



