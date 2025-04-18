import sys
import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory

class BaseGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # configure root window
        self.title("Define your analysis parameters")
        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.folder_path = tk.StringVar()
        self.avg_project = tk.BooleanVar()
        self.avg_project.set(False)
        self.max_project = tk.BooleanVar()
        self.max_project.set(True)
        self.single_plane = tk.BooleanVar()

        # create LUT dictionary and variables
        self.lut_dict = self.create_lut()
        self.channel1_var = tk.StringVar(value='Red')
        self.channel2_var = tk.StringVar(value='Cyan')
        self.channel3_var = tk.StringVar(value='Blue')
        self.channel4_var = tk.StringVar(value='Magenta')

        # file path selection widget
        self.file_path_entry = ttk.Entry(self, textvariable = self.folder_path)
        self.file_path_entry.grid(row = 0, column = 0, padx = 10, sticky = 'E')
        self.file_path_button = ttk.Button(self, text = 'Select folder')
        # self.folder_path.set('/Users/domchom/Documents/GitHub/Bruker_to_ImageJ/tests/test_data/single_plane')
        self.file_path_button['command'] = self.get_folder_path
        self.file_path_button.grid(row = 0, column = 1, padx = 10, sticky = 'W')

        # create max project button
        self.max_project_button = ttk.Checkbutton(self, variable = self.max_project, text = ' Max Project z-stacks?')
        self.max_project_button.grid(row = 1, column = 0, padx = 10, sticky = 'W')  

        # create avg project button
        self.avg_project_button = ttk.Checkbutton(self, variable = self.avg_project, text = ' AVG Project z-stacks?')
        self.avg_project_button.grid(row = 2, column = 0, padx = 10, sticky = 'W')  

        # create single-plane button
        self.single_plane_button = ttk.Checkbutton(self, variable = self.single_plane, text = ' Single Plane data?')
        self.single_plane_button.grid(row = 3, column = 0, padx = 10, sticky = 'W')  
        
        # create start button
        self.start_button = ttk.Button(self, text = 'Start conversion')
        self.start_button['command'] = self.start_analysis
        self.start_button.grid(row = 9, column = 0, padx = 10, sticky = 'E')

        # create cancel button
        self.cancel_button = ttk.Button(self, text = 'Cancel')
        self.cancel_button['command'] = self.cancel_analysis
        self.cancel_button.grid(row = 9, column = 1, padx = 10, sticky = 'W')

        # create LUT selection widgets
        self.channel1_menu = ttk.Combobox(self, textvariable=self.channel1_var, values=list(self.lut_dict.keys()))
        self.channel2_menu = ttk.Combobox(self, textvariable=self.channel2_var, values=list(self.lut_dict.keys()))
        self.channel3_menu = ttk.Combobox(self, textvariable=self.channel3_var, values=list(self.lut_dict.keys()))
        self.channel4_menu = ttk.Combobox(self, textvariable=self.channel4_var, values=list(self.lut_dict.keys()))
        self.channel1_menu.grid(row=0, column=3)
        self.channel2_menu.grid(row=1, column=3)
        self.channel3_menu.grid(row=2, column=3)
        self.channel4_menu.grid(row=3, column=3)

        self.ch1_label = ttk.Label(self, text="Ch1 LUT")
        self.ch2_label = ttk.Label(self, text="Ch2 LUT")
        self.ch3_label = ttk.Label(self, text="Ch3 LUT")
        self.ch4_label = ttk.Label(self, text="Ch4 LUT")
        self.ch1_label.grid(row=0, column=2)
        self.ch2_label.grid(row=1, column=2)
        self.ch3_label.grid(row=2, column=2)
        self.ch4_label.grid(row=3, column=2)

    def get_folder_path(self):
        self.folder_path.set(askdirectory())

    def create_lut(self):
        # Define LUTs
        grays = np.tile(np.arange(256, dtype='uint8'), (3, 1))

        red = np.zeros((3, 256), dtype='uint8')
        red[0] = np.arange(256, dtype='uint8')

        green = np.zeros((3, 256), dtype='uint8')
        green[1] = np.arange(256, dtype='uint8')

        blue = np.zeros((3, 256), dtype='uint8')
        blue[2] = np.arange(256, dtype='uint8')

        magenta = np.zeros((3, 256), dtype='uint8')
        magenta[0] = np.arange(256, dtype='uint8')
        magenta[2] = np.arange(256, dtype='uint8')

        cyan = np.zeros((3, 256), dtype='uint8')
        cyan[1] = np.arange(256, dtype='uint8')
        cyan[2] = np.arange(256, dtype='uint8')

        yellow = np.zeros((3, 256), dtype='uint8')
        yellow[0] = np.arange(256, dtype='uint8')
        yellow[1] = np.arange(256, dtype='uint8')

        fire = np.zeros((3, 256), dtype='uint8')
        fire[0] = np.clip(np.arange(256) * 4, 0, 255)
        fire[1] = np.clip(np.arange(256) * 4 - 255, 0, 255)
        fire[2] = np.clip(np.arange(256) * 4 - 510, 0, 255)

        ice = np.zeros((3, 256), dtype='uint8')
        ice[1] = np.clip(np.arange(256) * 4, 0, 255)
        ice[2] = np.clip(np.arange(256) * 4, 0, 255)

        return {
            'Grays': grays,
            'Red': red,
            'Green': green,
            'Blue': blue,
            'Magenta': magenta,
            'Cyan': cyan,
            'Yellow': yellow,
            #'Fire': fire,
            #'Ice': ice
        }

    def cancel_analysis(self):
        sys.exit('You have cancelled the analysis')
    
    def start_analysis(self):
        self.folder_path = self.folder_path.get()
        self.max_project = self.max_project.get()
        self.avg_project = self.avg_project.get()
        self.single_plane = self.single_plane.get()
        self.channel1_var = self.lut_dict[self.channel1_var.get()]
        self.channel2_var = self.lut_dict[self.channel2_var.get()]
        self.channel3_var = self.lut_dict[self.channel3_var.get()]
        self.channel4_var = self.lut_dict[self.channel4_var.get()]
        
        # destroy the widget
        self.destroy()