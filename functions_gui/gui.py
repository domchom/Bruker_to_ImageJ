import sys
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
        self.max_project = tk.BooleanVar()
        self.max_project.set(True)

        # file path selection widget
        self.file_path_entry = ttk.Entry(self, textvariable = self.folder_path)
        self.file_path_entry.grid(row = 0, column = 0, padx = 10, sticky = 'E')
        self.file_path_button = ttk.Button(self, text = 'Select folder')
        self.folder_path.set('/Users/domchom/Desktop/untitled folder')
        self.file_path_button['command'] = self.get_folder_path
        self.file_path_button.grid(row = 0, column = 1, padx = 10, sticky = 'W')

        # create max project button
        self.max_project_button = ttk.Checkbutton(self, variable = self.max_project, text = ' Max Project Images?')
        self.max_project_button.grid(row = 1, column = 0, padx = 10, sticky = 'E')  
        
        # create start button
        self.start_button = ttk.Button(self, text = 'Start conversion')
        self.start_button['command'] = self.start_analysis
        self.start_button.grid(row = 9, column = 0, padx = 10, sticky = 'E')

        # create cancel button
        self.cancel_button = ttk.Button(self, text = 'Cancel')
        self.cancel_button['command'] = self.cancel_analysis
        self.cancel_button.grid(row = 9, column = 1, padx = 10, sticky = 'W')


    def get_folder_path(self):
        self.folder_path.set(askdirectory())

    def cancel_analysis(self):
        sys.exit('You have cancelled the analysis')
    
    def start_analysis(self):
        self.folder_path = self.folder_path.get()
        self.max_project = self.max_project.get()
        
        # destroy the widget
        self.destroy()
