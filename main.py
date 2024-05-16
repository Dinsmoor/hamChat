import socket
import sys
import select
import time
import threading
import tkinter as tk
from tkinter import filedialog
import json
import base64
import datetime
import os
import importlib.util
from ARDOPCFPlugin import ARDOPCFPlugin

info = """
This application is a simple chat application that interfaces with the ARDOPC client
the ARDOPC client is a TNC that uses the ARDOP protocol
and is used for digital communications over any audio band, but is most commonly used
in amateur radio for HF and VHF communications.
It uses tkinter for the GUI and the ARDOPCF client for the TNC

There are a couple bugs in the ARDOPCF client that I have found as of writing
    1. When we get a data buffer message from ardop, it has FECFEC at the beginning
        of the message. I don't know why that's a behavior of ARDOPC, but since
        FEC applications are uncommon (untested), it might just be a bug/something weird.
    2. The TNC will not always accept a FEC frame over the air, saying it is a duplicate in the console.
        No idea why this happens. Should look at source code to see how it detects duplicates.
    3. Controlling PTT is a pain in the ass, and a better solution needs to be made.
        Either block execution until the TNC responds, or do it in a more asyncronus manner.
    4. FECID will sometimes not trigger PTT but that's probably because of the beforementioned bugs

        
Some ideas:
    1. just block the program when we need to read the next buffer message
    . This means that we will have some responsiveness issues, but less likely that
    . we will miss a message from the tnc.
    2. All messages should be encoded as json, so we can extend our feature set
    . as needed, or even make a standard where this chat program is a small set
    . of different programs, all speaking the same language



"""


class ARDOPCFGUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("ARDOP Chat")
        self.geometry("500x600")
        self.settings = {
            'callsign': 'N0CALL',
            'gridsquare': 'AA00AA',
            'fec_mode': '4FSK.200.50S',
            'fec_repeats': 1,
            'use_message_history': 1
        }
        self.ardop = ARDOPCF(self)
        self.plugins = PluginManager('ARDOPCF_Plugins')
        try:
            self._load_settings_from_file()
            self.ardop.init_tnc()
        except FileNotFoundError:
            pass
        self.create_widgets()
        
        # make sure the sockets are closed when the application is closed
        self.protocol("WM_DELETE_WINDOW", self.ardop.close_all)
        self.message_history = []
        
        self.listen_for_messages()
        self.update_ui_ardop_state()

    def _save_settings_to_file(self):
        with open('chat_settings.json', 'w') as f:
            f.write(json.dumps(self.settings))

    def _load_settings_from_file(self):
        with open('chat_settings.json', 'r') as f:
            self.settings = json.loads(f.read())
        self.apply_settings()

    def _save_message_history(self):
        with open('message_history.txt', 'w') as f:
            for message in self.message_history:
                f.write(message+'\n')
    
    def _load_message_history(self):
        with open('message_history.txt', 'r') as f:
            self.message_history = f.readlines()

    def create_widgets(self):
        # this is the main chat window and will return the messages from the ARDOPC client
        # from the receive buffer. We do not enter commands here, only messages.
        self.message_box = tk.Text(self, width=60, height=20)
        # make the message box scrollable
        self.scrollbar = tk.Scrollbar(self, command=self.message_box.yview)
        self.message_box.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # load the message history into the message box window, if enabled
        if self.settings['use_message_history']:
            try:
                self._load_message_history()
                for message in self.message_history:
                    self.message_box.insert(tk.END, message)
            except FileNotFoundError:
                pass
        # message box should not be editable, we will need to toggle this to update
        self.message_box.config(state=tk.DISABLED)

        self.message_box.pack()
        self.entry = tk.Entry(self, width=60)
        self.entry.bind("<Return>", lambda event: self.send_message())
        self.entry.pack()
        self.send_button = tk.Button(self, text="Send", command=self.send_message)
        #disable the send button until the user enters a message
        self.send_button['state'] = 'disabled'
        self.entry.bind("<Key>", lambda event: self.send_button.config(state='normal'))
        self.send_button.pack()

        # button to add a file to the buffer
        self.add_file_button = tk.Button(self, text="Add File", command=self.select_file)
        self.add_file_button.pack()

        self.clear_buffer_button = tk.Button(self, text="Clear Buffer", command=self.ardop.clear_buffer)
        self.clear_buffer_button.pack()
        self.settings_button = tk.Button(self, text="Settings", command=self.create_settings_menu)
        self.settings_button.pack()

        self.ardop_state_label = tk.Label(self, text="ARDOP State:")
        self.ardop_state_label.pack(side=tk.LEFT)
        self.ardop_state_string = tk.StringVar()
        self.ardop_state = tk.Label(self, textvariable=self.ardop_state_string)
        self.ardop_state.pack(side=tk.LEFT)

        self.ardop_buffer_string = tk.StringVar()
        self.ardop_buffer_label = tk.Label(self, text="ARDOP Buffer:")
        self.ardop_buffer_label.pack(side=tk.LEFT)
        self.ardop_buffer = tk.Label(self, textvariable=self.ardop_buffer_string)
        self.ardop_buffer.pack(side=tk.LEFT)

    def write_message(self, message):
        self.message_box.config(state=tk.NORMAL)
        self.message_box.insert(tk.END, message+'\n')
        if self.settings['use_message_history']:
            self.message_history.append(message)
            if len(self.message_history) > 500:
                self.message_history.pop(0)
        self.message_box.config(state=tk.DISABLED)

    def send_message(self):
        message = self.entry.get()
        message = self.settings['callsign'] + ': ' + message
        if self.ardop.send_text_to_buffer(message):
            transmit_thread = threading.Thread(target=self.ardop.transmit_buffer)
            transmit_thread.start()
        else:
            self.write_message("Could not send message, file too large or other error.")

        self.entry.delete(0, tk.END)
        self.write_message(message)
        self.send_button['state'] = 'disabled'
        self._save_message_history()

    def select_file(self):
        filename = filedialog.askopenfilename()
        self.ardop.load_file_to_buffer(filename)
        file_length = len(open(filename, 'rb').read())
        self.write_message(f"{filename} added to buffer, {file_length} bytes")
        self.send_button['state'] = 'normal'
        self._save_message_history()
    
    def save_file_to_disk(self, data):
        filename = filedialog.asksaveasfilename()
        with open(filename, 'wb') as f:
            f.write(data)
        self.write_message(f"File saved to {filename}")
        self._save_message_history()


    def listen_for_messages(self):
        message = self.ardop.recieve_from_data_buffer()
        if message:
            if 'FileXFR:' in message[:20]:
                # this is a file, decode the base64
                # split off the FileXFR: part
                data = message.split(":")[-1]
                file = base64.b64decode(data).decode()
                # save the file to disk
                self.save_file_to_disk(file)
            print(f"Received message: {message}")
            self.write_message(message)
            self._save_message_history()
        self.after(1000, self.listen_for_messages)
    
    def update_ui_ardop_state(self):
        self.ardop.cmd_response(command='STATE', wait=False)
        self.ardop.cmd_response(command='BUFFER', wait=False)
        self.ardop_state_string.set(self.ardop.state['state'])
        self.ardop_buffer_string.set(self.ardop.state['buffer'])

        self.after(200, self.update_ui_ardop_state)
    
    def create_settings_menu(self):
        self.settings_menu = tk.Toplevel(self)
        self.settings_menu.title("Settings")
        self.settings_menu.geometry("300x300")

        self.callsign_label = tk.Label(self.settings_menu, text="Callsign")
        self.callsign_label.pack()
        self.callsign_entry = tk.Entry(self.settings_menu)
        self.callsign_entry.insert(0, self.settings['callsign'])
        self.callsign_entry.pack()

        self.gridsquare_label = tk.Label(self.settings_menu, text="Gridsquare")
        self.gridsquare_label.pack()
        self.gridsquare_entry = tk.Entry(self.settings_menu)
        self.gridsquare_entry.insert(0, self.settings['gridsquare'])
        self.gridsquare_entry.pack()

        self.fec_mode_label = tk.Label(self.settings_menu, text="FEC Mode")
        self.fec_mode_label.pack()
        self.fec_mode_var = tk.StringVar(self.settings_menu)
        self.fec_mode_var.set(self.settings['fec_mode'])
        self.fec_mode_menu = tk.OptionMenu(self.settings_menu, self.fec_mode_var, *self.ardop.fec_modes)
        self.fec_mode_menu.pack()

        self.fec_repeats_label = tk.Label(self.settings_menu, text="FEC Repeats")
        self.fec_repeats_label.pack()
        self.fec_repeats_entry = tk.Scale(self.settings_menu, from_=0, to=5, orient=tk.HORIZONTAL)
        self.fec_repeats_entry.set(self.settings['fec_repeats'])
        self.fec_repeats_entry.pack()

        # checkbox for enabling saving and loading of message history
        self._save_message_history_var = tk.IntVar()
        self._save_message_history_var.set(1)
        self._save_message_history_checkbutton = tk.Checkbutton(self.settings_menu, text="Save Message History", variable=self._save_message_history_var)
        self._save_message_history_checkbutton.pack()

        self.save_button = tk.Button(self.settings_menu, text="Save", command=self.save_settings)
        self.save_button.pack()
        self.cancel_button = tk.Button(self.settings_menu, text="Cancel", command=self.settings_menu.destroy)
        self.cancel_button.pack()

    def save_settings(self):
        self.settings['callsign'] = self.callsign_entry.get()
        self.settings['gridsquare'] = self.gridsquare_entry.get()
        self.settings['fec_mode'] = self.fec_mode_var.get()
        self.settings['fec_repeats'] = self.fec_repeats_entry.get()
        self.settings['use_message_history'] = self._save_message_history_var.get()
        self.apply_settings()
        print(self.settings)
        self._save_settings_to_file()
        # put in message box the new settings
        self.write_message(f"Client Settings Updated")
        self.settings_menu.destroy()
    
    def apply_settings(self):
        self.ardop.callsign = self.settings['callsign']
        self.ardop.gridsquare = self.settings['gridsquare']
        self.ardop.fec_mode = self.settings['fec_mode']
        self.ardop.fec_repeats = self.settings['fec_repeats']
        self.ardop.cmd(f'MYCALL {self.settings["callsign"]}')
        self.ardop.cmd(f'GRIDSQUARE {self.settings["gridsquare"]}')
        self.ardop.cmd(f'FECMODE {self.settings["fec_mode"]}')
        self.ardop.cmd(f'FECREPEATS {self.settings["fec_repeats"]}')


class ARDOPCF:
    def __init__(self, ui=None):
        self.kill = False
        # the idea is we can store whatever we get here,
        # then when something needs it, we can just pop it off
        # because we did the action that needed the response
        self.command_response_history = []
        if ui:
            self.ui = ui
        else:
            self.ui = None

        try:
            self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_cmd.connect(('localhost', 8515))
            self.sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_data.connect(('localhost', 8516))
        except:
            print("Could not connect to ARDOPC client on ports 8515 and 8516 on this machine. Is it running?")
            print("Pointless to continue without a connection to the ARDOPC client.")
            print("Exiting.")
            exit(1)
        try:
            self.sock_rigctld = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_rigctld.connect(('localhost', 4532))
        except ConnectionRefusedError:
            print("Could not connect to rigctld on port 4532 on this machine. Is it running?")
            print("You will not be able to key the transmitter.")
            print("If you are using VOX (You should use CAT), you can type 'y' and press enter to ignore this error.")
            choice = input("Press enter to continue.")
            if choice != 'y':
                print("Exiting.")
                exit(1)
            self.sock_rigctld = None

        self.callsign = 'N0CALL'
        self.gridsquare = 'AA00AA'
        self.fec_mode = '4FSK.200.50S'
        self.fec_repeats = 0

        self.fec_modes = [
            '4FSK.200.50S',
            '4PSK.200.100S',
            '4PSK.200.100',
            '8PSK.200.100',
            '16QAM.200.100',
            '4FSK.500.100S',
            '4FSK.500.100',
            '4PSK.500.100',
            '8PSK.500.100',
            '16QAM.500.100',
            '4PSK.1000.100',
            '8PSK.1000.100',
            '16QAM.1000.100',
            '4PSK.2000.100',
            '8PSK.2000.100',
            '16QAM.2000.100',
            '4FSK.2000.600',
            '4FSK.2000.600S'
        ]

        self.state = {
            'state': 'DISC',
            'buffer': 0,
            'ptt': False,
            'mycall': 'N0CALL',
            'gridsquare': 'AA00AA',
            'fec_mode': '4FSK.200.50S',
            'protocol_mode': 'FEC',
            'fec_repeats': 0,

        }

        # initialize the ARDOPC client
        self.init_tnc()
        self.listen_for_command_responses_thread = threading.Thread(target=self.listen_for_command_responses)
        self.listen_for_command_responses_thread.start()

    def init_tnc(self):
        self.cmd_response(command='INITIALIZE')
        self.cmd_response(command=f'MYCALL {self.callsign}')
        self.cmd_response(command=f'GRIDSQUARE {self.gridsquare}')
        self.cmd_response(command='PROTOCOLMODE FEC')
        self.cmd_response(command=f'FECMODE {self.fec_mode}')
        self.cmd_response(command=f'FECREPEATS {self.fec_repeats}')
        self.cmd_response(command='FECID 1')
        self.cmd_response(command='LISTEN 1')
        self.cmd_response(command='ENABLEPINGACK 1')
        self.cmd_response(command='USE600MODES 1') # symbol rate violation if on HF >:^)
        time.sleep(0.25)

    def cmd(self, string):
        # Append the Carriage Return byte to the string
        string += '\r'
        self.sock_cmd.sendall(string.encode())


    def key_transmitter(self):
        if self.sock_rigctld:
            print("PTT ON->rigctld")
            # Send the command to key the transmitter
            self.sock_rigctld.sendall(b'T 1\n')
        else:
            print("Cannot key transmitter, rigctld not connected")
    
    def unkey_transmitter(self):
        if self.sock_rigctld:
            print("PTT OFF->rigctld")
            # Send the command to unkey the transmitter
            self.sock_rigctld.sendall(b'T 0\n')
        else:
            print("Cannot unkey transmitter, rigctld not connected")
    
    def send_text_to_buffer(self, message : str):
        # this application only uses FEC mode
        # data format is <2 bytes for length><FEQ or ARQ><data>
        data = 'FEC' + message
        if len(data) > 2000:
            print("Message too long, TNC cannot send.")
            return(False)
        try:
            data_length = len(data).to_bytes(2, 'big')
        except OverflowError:
            print("Message too long, cannot send.")
            return(False)
        data = data_length + data.encode()
        # check the actual length of the message
        self.sock_data.sendall(data)
        print(f"->buffer: '{message}'")
        return(True)
        # the buffer amount will be polled elsewhere

    def append_bytes_to_buffer(self, data : bytes):
        # this application only uses FEC mode
        # data format is <2 bytes for length><FEQ or ARQ><data>
        data = 'FEC' + data.decode()
        # our maximum data length we can load is 65535 bytes (at a time, anyway)
        # we may be able to load more data if we split it up into multiple messages
        # too tired to figure that out right now
        data_length = len(data).to_bytes(2, 'big')
        data = data_length + data.encode()
        self.sock_data.sendall(data)

    def load_file_to_buffer(self, filename):
        # just for testing right now, it does work.
        with open(filename, 'rb') as f:
            file = f.read()
        # encode as base64 (Do we even need to do this? It causes OverflowError if too large)
        file = base64.b64encode(file).decode()
        self.send_text_to_buffer("FileXFR:" + file)


    def transmit_buffer(self):
        self.cmd_response(command='FECSEND TRUE', wait=False)

    def clear_buffer(self):
        self.cmd('PURGEBUFFER')

    def recieve_from_data_buffer(self):
        # The TNC decodes audio, if there is a valid packet,
        # it puts into the data buffer.
        # Duplicate frames will not be passed to the host.
        try:
            if self.sock_data in select.select([self.sock_data], [], [], 0)[0]:
                raw_response = self.sock_data.recv(1024)
                # first two bytes are the length of the message, not used here for now
                # (we will foolishly assume we get the entire message in one go)
                message_length = int.from_bytes(raw_response[:2], 'big')
                raw_response = raw_response[2:]
                # next six bytes are "FECFEC", which we can trim
                raw_response = raw_response[6:]
                try:
                    response = raw_response.decode()
                    # this is very innefficent performance wise.
                    # I think implementing some kind of hook/plugin system would
                    # allow for this simple chat application to be extended with
                    # more features, like psuedo-connected modes, or relaying messages
                    # Basically, adding whatever protocol we want to the ARDOPC client
                    if response.startswith('FileXFR:'):
                        # this is a file, decode the base64
                        response = base64.b64decode(response[8:]).decode()
                except UnicodeDecodeError:
                    filename = f"invalid_packet_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.bin"
                    print(f"Received invalid data response: {raw_response}, saved to {filename}")
                    # if we end up getting an invalid response, it probably means this client is
                    # incompatible with whatever protocol built on top of this that we received
                    # for example, if we received a raw binary file, or gzipped, we would not be
                    # able to decode it here.
                    with open(filename, 'wb') as f:
                        f.write(raw_response)
                return(response)
        except OSError as e:
            return(None)
        
    def cmd_response(self, command=None, wait=False):
        # if we run without a command, return immediately
        # if we run with a command, block until we get a response
        while True:
            timeout = 0
            if command:
                self.cmd(command)
            if wait:
                timeout = None
            else:
                return(None)
            try:
                # check if there is data to be read from the socket.
                # None timeout means we will block until we get a response
                # 0 timeout means we will return immediately, response or not
                if self.sock_cmd in select.select([self.sock_cmd], [], [], timeout)[0]:
                    response = self.sock_cmd.recv(1024).decode()
                    return(response)
            except OSError as e:
                return(None)
    
    def listen_for_command_responses(self):
        # this is our main loop for handling responses from the TNC
        while True:
            if self.kill:
                return
            response = self.cmd_response(wait=True)
            self.command_response_history.append(response)

            try:
                for entry in self.command_response_history:
                    if ('PTT TRUE' in entry) or ('T T' in entry):
                        self.state['ptt'] = True
                        self.key_transmitter()
                        self.command_response_history.remove(entry)
                    elif ('PTT FALSE' in entry) or ('T F' in entry):
                        self.state['ptt'] = False
                        self.unkey_transmitter()
                        self.command_response_history.remove(entry)
                    elif entry.startswith('BUFFER'):
                        self.state['buffer'] = entry.split()[1]
                        self.command_response_history.remove(entry)
                    elif entry.startswith('STATE'):
                        self.state['state'] = entry.split()[1]
                        self.command_response_history.remove(entry)
                    elif entry.startswith('FECSEND'):
                        self.command_response_history.remove(entry)
                    elif entry.startswith('MYCALL'):
                        self.state['mycall'] = entry.split()[2]
                        self.command_response_history.remove(entry)
                    elif entry.startswith('GRIDSQUARE'):
                        self.state['gridsquare'] = entry.split()[2]
                        self.command_response_history.remove(entry)
                    elif entry.startswith('FECMODE'):
                        self.state['fec_mode'] = entry.split()[2]
                        self.command_response_history.remove(entry)
                    elif entry.startswith('FECREPEATS'):
                        self.state['fec_repeats'] = entry.split()[2]
                        self.command_response_history.remove(entry)
                    elif entry.startswith('PROTOCOLMODE'):
                        self.state['protocol_mode'] = entry.split()[2]
                        self.command_response_history.remove(entry)
                    else:
                        print(f"Unhandled command response: {entry}")
                        self.command_response_history.remove(entry)
            except TypeError:
                pass

    def close_all(self):
        print("Halting transmission, closing all sockets, and exiting")
        self.kill = True
        self.unkey_transmitter()
        self.sock_cmd.close()
        self.sock_data.close()
        if self.sock_rigctld:
            self.sock_rigctld.close()
        sys.exit()



class PluginManager:
    def __init__(self, plugin_folder):
        self.plugins = []
        # make the plugin folder if it doesn't exist
        if not os.path.exists(plugin_folder):
            os.makedirs(plugin_folder)
            # save the core plugin to the plugin folder

        sys.path.append(plugin_folder)
        self.load_plugins(plugin_folder)

    def load_plugins(self, plugin_folder):
        for filename in os.listdir(plugin_folder):
            if filename.endswith('.py'):
                spec = importlib.util.spec_from_file_location(filename[:-3], os.path.join(plugin_folder, filename))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    if attr_name.startswith('ARDOPCFPlugin'):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, ARDOPCFPlugin):
                            self.plugins.append(attr())

    def list_plugins(self):
        for plugin in self.plugins:
            print(plugin.__class__.__name__)
            print(plugin.info)

    def on_data_received(self, data):
        for plugin in self.plugins:
            plugin.on_data_received(data)
    
    def on_command_received(self, command):
        for plugin in self.plugins:
            plugin.on_command_received(command)

    def on_data_loaded_into_buffer(self, data):
        for plugin in self.plugins:
            plugin.on_data_loaded_into_buffer(data)
    
    def on_file_loaded_into_buffer(self, filename):
        for plugin in self.plugins:
            plugin.on_file_loaded_into_buffer(filename)
    
    def on_file_saved_to_disk(self, filename):
        for plugin in self.plugins:
            plugin.on_file_saved_to_disk(filename)
    
    def on_transmit_buffer(self):
        for plugin in self.plugins:
            plugin.on_transmit_buffer()
    
    def on_clear_buffer(self):
        for plugin in self.plugins:
            plugin.on_clear_buffer()

    def on_key_transmitter(self):
        for plugin in self.plugins:
            plugin.on_key_transmitter()
    
    def on_unkey_transmitter(self):
        for plugin in self.plugins:
            plugin.on_unkey_transmitter()

    def on_initialize(self):
        for plugin in self.plugins:
            plugin.on_initialize()
    
    def on_ui_create_settings_menu(self):
        for plugin in self.plugins:
            plugin.on_ui_create_settings_menu()
    
    def on_ui_save_settings(self):
        for plugin in self.plugins:
            plugin.on_ui_save_settings()

    def on_ui_create_widgets(self):
        for plugin in self.plugins:
            plugin.on_ui_create_widgets()


pluginCoreText = """
# will place ARDOPCFPluginCore(ARDOPCFPlugin): here so we can import it
# from within the plugin manager
"""



# all valid commands in HostInterface.c
valid_prefix_commands = [
    'ABORT',
    'ARQBW',
    'ARQCALL',
    'ARQTIMEOUT',
    'BREAK',
    'BUFFER',
    'BUSYBLOCK',
    'BUSYDET',
    'CALLBW',
    'CAPTURE',
    'CAPTUREDEVICES',
    'CL',
    'CLOSE',
    'CMDTRACE',
    'CODEC',
    'CONSOLELOG',
    'CWID',
    'DATATOSEND',
    'DEBUGLOG',
    'DISCONNECT',
    'DRIVELEVEL',
    'ENABLEPINGACK',
    'EXTRADELAY',
    'FASTSTART',
    'FECID',
    'FECMODE',
    'FECREPEATS',
    'FECSEND',
    'FSKONLY',
    'GRIDSQUARE',
    'INITIALIZE',
    'LEADER',
    'LISTEN',
    'LOGLEVEL',
    'MONITOR',
    'MYAUX',
    'MYCALL',
    'PAC',
    'PING',
    'PLAYBACK',
    'PLAYBACKDEVICES',
    'PROTOCOLMODE',
    'PURGEBUFFER',
    'RADIOFREQ',
    'RADIOHEX',
    'RADIOPTTOFF',
    'RADIOPTTON',
    'RXLEVEL',
    'SENDID',
    'SQUELCH',
    'STATE',
    'TRAILER',
    'TUNINGRANGE',
    'TXLEVEL',
    'TWOTONETEST',
    'USE600MODES',
    'VERSION',
]


ardop_fec_session_rules = """
                                                FEC SESSION RULES

FEC sessions are between a sending station and 1 or more receiving stations (multicast). FEC sessions are simpler than
ARQ connections and use a combination of Forward Error Correcting codes and optional repeating of frames to improve
the likelihood of error-free reception by the multiple receiving stations. Since there is no active back channel (no
ACKs/NAKs) with FEC sessions there can be no guarantee of error free data delivery. The sending station may select to
repeat the data from 0 (no repeats) to 5 repeats. If any one of the repeated frames is received correctly by the FEC
receiving station the result will be error free. Duplicate data from FEC repeats is not passed by the FEC receiving station
to the Host.

1.0 Starting a FEC session. (Both FEC sending station and the FEC receiving station(s) are assumed to be on line
(“sound cards” sampling) and in the DISC state. The Sending station normally begins a FEC session with an
optional ID frame (the same as used in ARQ sessions) and then sends data frames using the sending stations
selected bandwidth (200, 500, 1000, or 2000 Hz and Data mode (4PSK, 8PSK, 16QAM, or 4FSK). In an FEC
session the most robust data modes (usually nFSK) are often used to improve robustness. Since there is no “back
channel” there is no “gear shifting” to increase net throughput or change robustness modes. Repeats improve
the likelihood of correct reception but at the expense of reduced net throughput. After each data transmission
(or repeated group if using repeats) the FEC sending station toggles the Odd/Even frame type. If the stations
sending FEC data sends for more than 10 minutes an automatic ID frame is inserted (for legal ID) this is identified
as an ID frame and transferred to the host by receiving station. The host can choose to display or ignore the ID
data. When all data (including repeats) is sent the FEC Sending station sends returns to the DISC state.

2.0 Receiving FEC data. When a station in the DISC state detects a Data frame it goes to the FEC Rcv state and
begins decoding FEC data. If the sending station is using repeated FEC frames the receiving station waits until it
has received a perfect frame (no CRC error) and then passes that frame to the Host as error free FEC data. If no
error free data is received before the FEC sending station toggles the FEC Data Odd/Even frame type the FEC
Receiving station passes any received data (with errors) to the host flagging it as “containing errors”. The host
can then either display the data in a distinctive way (e.g. RED or strikethrough text) or simply ignore the data.
After each received frame the FEC receiving station returns to the DISC state

                        VALID FEC DATA RATES

const char strAllDataModes[18][15] =
		{"4FSK.200.50S", "4PSK.200.100S",
		"4PSK.200.100", "8PSK.200.100", "16QAM.200.100",
		"4FSK.500.100S", "4FSK.500.100",
		"4PSK.500.100", "8PSK.500.100", "16QAM.500.100",
		"4PSK.1000.100", "8PSK.1000.100", "16QAM.1000.100", 
		"4PSK.2000.100", "8PSK.2000.100", "16QAM.2000.100", 
		"4FSK.2000.600", "4FSK.2000.600S"};
"""


if __name__ == '__main__':
    # Create an instance of the ARDOPC class
    ardop_chat_ui = ARDOPCFGUI()
    ardop_chat_ui.mainloop()
