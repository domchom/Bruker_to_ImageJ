This workflow was written to batch import Bruker Files into ImageJ formats. It also imports the frame rate and the pixel size (assuming you set the correct objective.)

As of 230229, this is working for Files saved on the SFC and confocal.
- will likely only work with timeseries, not just zstack, single images
- will need to have the MIP saved already from the scope
- should work with whatever number of channels, but have only tested 2-3

To use: use the main_workflow.py. You will need to copy and paste the path in the variable "parent_folder_path"