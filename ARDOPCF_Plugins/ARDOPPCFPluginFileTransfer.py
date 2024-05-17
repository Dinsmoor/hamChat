# inherits from ARDOPCFPlugin
from ..ARDOPCFPlugin import ARDOPCFPlugin
# import to assist with type hinting
from ..main import ARDOPCFGUI
import tkinter as tk
from tkinter import filedialog


class ARDOPCFPluginFileTransfer(ARDOPCFPlugin):
    def __init__(self, host_interface=ARDOPCFGUI):
        super().__init__(host_interface)
        self.info = """
        This is the main plugin for the ARDOP Chat application.
        It allows for simple file transfer between two ARDOP Chat clients.
        """
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Simple File Transfer',
            'version': '0.1',
            'description': self.info,
            'protocol_identifier': 'FileXfr',
            'handlers': ['FileXfr'],
            'expected_header': "CALLSIGN:FileXfr:0.1:FILENAME:FILESIZE:BEGIN:",
            'provides': self.__class__.__name__,
            'depends_on': [{'plugin': 'ARDOPCFPluginCore', 'version': '0.1'}],
        }
    
    def on_data_received(self, data : dict) -> bytes:
        '''data should be a dictionary with a header and a payload both of type bytes'''

        # expected header for FileXfr: CALLSIGN:FileXfr:0.1:FILENAME:FILESIZE:BEGIN:
        suggested_filename = data['header'].split(b':')[3]

        if len(data['payload']) != data['header'].split(b':')[4]:
            self.host_interface.write_message(f"File transfer error: file size mismatch. Saving anyway.")
        self._save_file_to_disk(data['payload'], suggested_filename)
    
    def on_ui_create_widgets(self):
        # button to add a file to the buffer
        # not sure if this will work.
        self.host_interface.add_file_button = tk.Button(self, text="Add File", command=self._select_file)
        self.host_interface.add_file_button.pack()
        
    def _select_file(self):
        filename = filedialog.askopenfilename()
        self._load_file_to_buffer(filename)
        file_length = len(open(filename, 'rb').read())
        self.host_interface.write_message(f"{filename} added to buffer, {file_length} bytes")
        self.host_interface.send_button['state'] = 'normal'
        self.host_interface.save_message_history()
    
    def _save_file_to_disk(self, data: bytes, suggested_filename: str = None):
        filename = filedialog.asksaveasfilename(initialfile=suggested_filename,)
        with open(filename, 'wb') as f:
            f.write(data)
        self.host_interface.write_message(f"File saved to {filename}")
        self.host_interface.save_message_history()
    
    def _load_file_to_buffer(self, filename):
        callsign = self.host_interface.settings['callsign']
        proto = self.definition['protocol_identifier']
        proto_ver = self.definition['version']
        with open(filename, 'rb') as f:
            file = f.read()
            filesize = len(file)
            header = f"{callsign}:{proto}:{proto_ver}:{filename}:{filesize}:BEGIN:"
            data = header.encode() + file
            self.host_interface.ardop.append_bytes_to_buffer(data)
        self.host_interface.write_message(f"{filename} added to buffer, {filesize} bytes")

