import tkinter as tk
from hamChatPlugin import hamChatPlugin
import json

"""
hamChat features a standard header format. This is used to identify the sender,
the plugin, the version of the plugin, the recipients,
and the beginning and end of the payload. Plugin authors are able to add custom
fields to the header, but the standard fields should be present. This is so the data
can be routed to the correct plugin, and the plugin can identify the sender and recipients,
although it certainly adds significant overhead to short data transmissions.

Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

bands = ["160m", "80m", "40m", "20m", "17m" "15m", "12m" "10m", "6m", "2m", "1.25m", "70cm"]
# all frequencies are in Hz, must be padded to 9 digits for Hamlib
# dedicated ALE frequencies are not yet defined. Just for testing.
default_freqs = {
    "160m": "001800000",
    "80m": "003500000",
    "40m": "007100000",
    "20m": "014100000",
    "17m": "018100000",
    "15m": "021300000",
    "12m": "024900000",
    "10m": "028300000",
    "6m": "050300000",
    "2m": "144200000",
    "1.25m": "222100000",
    "70cm": "432100000",
}

#class ArdopALE(hamChatPlugin):
class ArdopALE:
    def __init__(self, host_interface):
        self.header_id = 'ALE'
        self.info = """Uses ARDOPCF and Hamlib for two stations to
        find each other over a varaity of bands and establish a connection.
        Because this is application layer, it is VERY INEFFICIENT as far as
        time. It is VERY SLOW to handshake because I cannot directly command
        short ardop frames like CONREQ, CONACK, and DATAACK, (part of ARQ mode)
        all which are very short and robust. This is a fun proof of concept.
        """
        # Frame codes 31-38 are CONREQ frames that are shorter than 4FSK20050S, but we
        # do not have a way to directly use them. If we initiate an ARQ connection, we
        # could very well save time that way, however, the ARDOP modem itself has too
        # much control over the connection. We could use the ARQ mode to establish a
        # connection, then switch to FEC mode for data transfer if we wanted to.

        self.host_interface = host_interface


        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'url': 'https://github.com/Dinsmoor/hamChat',
            'name': 'ardopALE',
            'version': '0.1',
            'description': self.info,
            'transport': '',
            'handlers': [self.header_id],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'},
                           {'plugin': 'ARDOPCF', 'version': '0.1'},
                           {'plugin': 'Hamlib', 'version': '0.1'}],
        }

        self.settings = {
        }
        self.usable_bands = []
        self.current_band = ''
        self.band_index = 0
        self.connected = False
        # acceptible values for ale_handshake_stage['stage'] are:
        # off: we are not trying to connect to anyone, and we are not listening for ALE
        # idle: we are not trying to connect to anyone, but we are listening for ALE calls
        # calling: we are trying to connect to someone, awaiting a response
        # confirming: we are responding to a call, awaiting a link confirmation response
        # connected: we are connected to another station
        self.ale_handshake_stage = {'station': '', 'stage': 'off'}
        self.last_heard_station = None
        
        self.ale_listen = tk.BooleanVar()
        self.load_config_from_file()

    def on_payload_recieved(self, data: dict):
        '''This method is called by the main application when a data frame is received from the selected transport.

        In your plugin, this is where you would handle incoming data that you have registered as a handler for.

        It is a dictionary containing any hamChat header and the payload.
        If you use "ALL" in your handlers, you may recieve nonstandard data, containing only a payload.

        When it gets here, it will be a dictionary like this:
        {'header': b'SENDER:PLUGINNAME:PLUGINVERSION:RECIPENTS:BEGIN:', 'payload': b'<DATA>'}
        '''
        if not self.ale_listen.get():
            return
        if self.header_id not in data['header'][1].decode():
            return
        # check if we are the recipient, or if it is a broadcast
        if data['header'][3] == 'ALL' or data['header'][3] == self.host_interface.get_callsign():
            print(f"ALE handshake received: {data['payload'].decode()}")
            self.last_heard_station = data['header'][0].decode()
            self.last_freq = self.host_interface.IPC('Hamlib', self.definition['name'], 'get_radio_frequency')
            self.ale_handshake(data['header'][0].decode())

    def create_frequency_tuning_schedule(self):
        '''This method creates a list of frequencies to tune to in order to find a station.'''
        pass

    def tune_next_frequency(self):
        current_freq = self.host_interface.IPC('Hamlib', self.definition['name'], 'get_radio_frequency')
        
        

    def save_config_to_file(self):
        with open('plugins/ale_config.json', 'w') as f:
            json.dump({'bands': self.usable_bands}, f)

    def load_config_from_file(self):
        try:
            with open('plugins/ale_config.json', 'r') as f:
                config = json.load(f)
                self.usable_bands = config['bands']
        except FileNotFoundError:
            self.save_config_to_file()

    def save_configuration(self, band_vars):
        self.usable_bands = [band for band in band_vars if band_vars[band].get()]
        self.save_config_to_file()
        self.config_window.destroy()

    def create_configuration_window(self):
        self.config_window = tk.Toplevel()
        self.config_window.title('ARDOP ALE Configuration')
        self.config_window.geometry('400x400')

        # Dictionary to store the IntVar objects associated with each band
        band_vars = {band: tk.IntVar() for band in bands}

        # Create a checkbutton for each band
        for band in bands:
            checkbutton = tk.Checkbutton(self.config_window, text=band, variable=band_vars[band])
            checkbutton.pack()
        # Create a button to save the configuration
        save_button = tk.Button(self.config_window, text='Save', command=lambda: self.save_configuration(band_vars))
        save_button.pack()

    def make_ale_call(self, station: str):
        self.ale_handshake(station)

    def ale_handshake(self, station: str):
        sender = self.host_interface.get_callsign()
        standard_frame = f"{sender}:{self.header_id}:{self.definition['version']}:{station}:BEGIN::END:"
        self.host_interface.plugMgr.IPC('ARDOPCF', self.definition['name'], command='send', data=standard_frame.encode())

    def create_plugin_frame(self, tkParent) -> tk.Frame:
        ale_frame = tk.Frame(tkParent)
        ale_frame.pack()
        # checkbutton to enable ALE listening/response
        listen_button = tk.Checkbutton(ale_frame, text='Listen for ALE')
        listen_button.pack()
        # button to call the entered recipient
        call_button = tk.Button(ale_frame, text='Call')
        call_button.pack()

        # Create a button to open the configuration window
        config_button = tk.Button(ale_frame, text='Configuration', command=self.create_configuration_window)
        config_button.pack()

        return ale_frame

    def update_plugin_frame(self):
        '''This method is called when the main application wants to update the plugin's frame.
        This is where you would update any tk variables that are displayed in the plugin's frame.'''
        pass

    def on_settings_update(self):
        '''This method is called when the settings are updated.
        This is where you might update/save your plugin's settings.
        Since plugins are likely to implement tk widgets with tk variables,
        it would be wise to declare them beforehand with defaults (or load any defaults)
        in __init__ and update them here.'''
        pass