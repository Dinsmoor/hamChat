# inherits from hamChatPlugin
from hamChatPlugin import hamChatPlugin
import tkinter as tk
from tkinter import filedialog

"""
Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

class SimpleFileTransfer(hamChatPlugin):
    def __init__(self, host_interface: object):
        super().__init__(host_interface)
        self.info = f"""
        This is a demo plugin for the hamChat application.
        It allows for simple file transfer between two hamChat clients.
        https://github.com/Dinsmoor/hamChat
        """
        self.header_id = 'FileXfr'
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Simple File Transfer',
            'version': '0.1',
            'description': self.info,
            'transport': '',
            'handlers': [self.header_id],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
    
    def on_payload_recieved(self, data : dict) -> bytes:
        '''data should be a dictionary with a header and a payload both of type bytes'''
        # example data: {'header': b'SENDER:FileXfr:0.1:RECIPIENTS:FILENAME:FILESIZE:BEGIN:', 'payload': b'<DATA>'}

        #                                 0       1     2     3        4        5        6
        # expected header for FileXfr: SENDER:FileXfr:0.1:RECIPIENTS:FILENAME:FILESIZE:BEGIN:
        suggested_filename = data['header'].split(b':')[4]

        if len(data['payload']) != data['header'].split(b':')[5]:
            self.host_interface.print_to_chatwindow(f"File transfer error: file size mismatch. Saving anyway." )
        self._save_file_to_disk(data['payload'], suggested_filename)
    
    def create_plugin_frame(self, tkParent):
        button_frame = tk.Frame(tkParent)
        self.plugin_label = tk.Label(button_frame, text=self.definition['name'])
        self.plugin_label.pack(side=tk.TOP)
        self.add_file_button = tk.Button(button_frame, text="Add File", command=self._select_file)
        self.add_file_button.pack(side=tk.LEFT)
        self.send_file_button = tk.Button(button_frame, text="Send File", command=self.host_interface.plugMgr.on_transmit_buffer)
        self.send_file_button.pack(side=tk.LEFT)
        button_frame.pack()
        
    def _select_file(self):
        filename = filedialog.askopenfilename()
        # handle if user presses cancel
        if not filename:
            return
        # filename only, not the full path
        filename_nopath = filename.split('/')[-1]
        self._load_file_to_buffer(filename)
        file_length = len(open(filename, 'rb').read())
        
        self.host_interface.print_to_chatwindow(f"{filename_nopath} added to buffer, {file_length} bytes" )
    
    def _save_file_to_disk(self, data: bytes, suggested_filename: str = None):
        filename = filedialog.asksaveasfilename(initialfile=suggested_filename,)
        # if the user cancels the save dialog, filename will be an empty string
        if not filename:
            return
        with open(filename, 'wb') as f:
            f.write(data)
        self.host_interface.print_to_chatwindow(f"File saved to {filename}" )
    
    def _load_file_to_buffer(self, filename):
        # Don't forget that we need to comply with the expected header format
        # first four fields, and BEGIN/END are required by hamchat to get you your data, the rest are up to you
        # SENDER:FileXfr:0.1:RECIPIENTS:{your fields here}BEGIN:
        callsign = self.host_interface.settings['callsign']
        recipients = self.host_interface.recipients.get()
        version = self.definition['version']
        with open(filename, 'rb') as f:
            file = f.read()
            filesize = len(file)
            filename_nopath = filename.split('/')[-1]
            header = f"{callsign}:{self.header_id}:{version}:{recipients}:{filename_nopath}:{filesize}:BEGIN:".encode()
            footer = b":END:"
            data = header + file + footer
            self.host_interface.plugMgr.append_bytes_to_buffer(data)
        self.host_interface.print_to_chatwindow(f"{filename} added to buffer, {filesize} bytes" )