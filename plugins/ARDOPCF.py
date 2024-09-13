import socket
import time
import threading
import tkinter as tk
from tkinter import ttk
import json
import os
#type help
from hamChatPlugin import hamChatPlugin
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import HamChat
else:
    HamChat = None

"""
Standard hamChat header format:
mycall my_plugin version yourcalls BEGIN my_message_or_data END
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

class ARDOPCF(hamChatPlugin):
    def __init__(self, host_interface: HamChat):
        self.info = """
        This plugin interfaces with the ARDOPC TNC to provide ARDOP transport for hamChat.
        Make sure ardopcf is running on localhost on ports 8515 and 8516.
        ex. ./ardopcf 8515 plughw:1,0 plughw:1,0
        Get ARDOPCF here: https://github.com/pflarue/ardop
        """
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'ARDOPCF',
            'version': '0.1',
            'description': self.info,
            'transport': 'ARDOP',
            'handlers': [],
            'protocol_fields': [],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
        self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.stop_event = threading.Event()
        self.data_transfer_complete = threading.Event()
        self.command_response_history = []
        self.pending_buffers = []
        self.host_interface = host_interface
        
        self.ready = tk.StringVar()
        self.ardop_status_label = tk.Label()
        self.transport_status_frame_text = tk.StringVar()
        self.status_frame = tk.Frame()

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

        self.rate_table = {
            # everything that's 0 is not in the datasheet.
            '4FSK.200.50S': 310,
            '4PSK.200.100S': 436,
            '4PSK.200.100': 756,
            '8PSK.200.100': 1286,
            '16QAM.200.100': 1512,

            '4FSK.500.100S': 0, 
            '4FSK.500.100': 0,
            '4PSK.500.100': 1509,
            '8PSK.500.100': 2566,
            '16QAM.500.100': 3024,

            '4PSK.1000.100': 3018,
            '8PSK.1000.100': 5133,
            '16QAM.1000.100': 6036,

            '4PSK.2000.100': 6144,
            '8PSK.2000.100': 10386,
            '16QAM.2000.100': 12072,
            '4FSK.2000.600': 0,
            '4FSK.2000.600S': 0
        }

        self.arq_bw_modes = [
            '2000MAX',
            '1000MAX',
            '500MAX',
            '200MAX',
            '2000FORCE',
            '1000FORCE',
            '500FORCE',
            '200FORCE',
        ]

        self.state = {
            # general states
            'host': 'localhost',
            'port': 8515,
            'state': 'DISC',
            'protocolmode': 'FEC', # FEC, ARQ, RXO
            'buffer': 0,
            'ptt': False,
            'mycall': 'N0CALL',
            'myaux': '',
            'gridsquare': 'AA00AA',
            'busydet': True,
            'drivelevel': '100', # 0-100
            'cwid': 'TRUE', # TRUE, ONOFF, FALSE
            'enablepingack': True,
            'ping_count': 1, # 1-15
            'extradelay': 0, # 0-100000
            'leader': 120, # 120-2500
            'listen': True,
            'loglevel': 7, # 0-8
            'monitor': False,
            'capture': '',
            'playback': '',
            'squelch': 5, # 1-10
            'trailer': 20, # 0-200
            'tuningrange': 100, # 0-200
            'use600modes': True,
            'version': '',
            # FEC mode states
            'fec_mode': '4FSK.200.50S',
            'protocol_mode': 'FEC',
            'fec_repeats': 0,
            'fecid': False,
            # ARQ mode states
            'arq_dialing_quantity': 2, # 2-15
            'arqbw': '1000MAX',
            'arqtimeout': 30, # 30-240
            'autobreak': True,
            'busyblock': True,
            'callbw': self.arq_bw_modes[2],
        }
        self._load_settings_from_file()

        # on protocolchange, we query ardopcf for these settings
        self.info_commands = [
            'state',
            'protocolmode', # FEC, ARQ, RXO
            'buffer',
            'mycall',
            'myaux',
            'gridsquare',
            'busydet',
            'drivelevel', # 0-100
            'cwid', # TRUE, ONOFF, FALSE
            'enablepingack',
            'extradelay', # 0-100000
            'leader', # 120-2500
            'listen',
            'loglevel', # 0-8
            'monitor',
            'capture',
            'playback',
            'squelch', # 1-10
            'trailer', # 0-200
            'tuningrange', # 0-200
            'use600modes',
            'version',
        ]

        self.ardop_host_var = tk.StringVar()
        self.ardop_host_var.set(self.state.get('host'))
        self.ardop_port_var = tk.IntVar()
        self.ardop_port_var.set(self.state.get('port'))
        self.state_var = tk.StringVar()
        self.state_var.set(self.state.get('state'))
        self.protocolmode_var = tk.StringVar()
        self.protocolmode_var.set(self.state.get('protocolmode'))
        self.buffer_var = tk.IntVar()
        self.buffer_var.set(self.state.get('buffer'))
        self.mycall_var = tk.StringVar()
        self.mycall_var.set(self.state.get('mycall'))
        self.myaux_var = tk.StringVar()
        self.myaux_var.set(self.state.get('myaux'))
        self.gridsquare_var = tk.StringVar()
        self.gridsquare_var.set(self.state.get('gridsquare'))
        self.busydet_var = tk.BooleanVar()
        self.busydet_var.set(self.state.get('busydet'))
        self.drivelevel_var = tk.StringVar()
        self.drivelevel_var.set(self.state.get('drivelevel'))
        self.cwid_var = tk.StringVar()
        self.cwid_var.set(self.state.get('cwid'))
        self.enablepingack_var = tk.BooleanVar()
        self.enablepingack_var.set(self.state.get('enablepingack'))
        self.ping_count_var = tk.IntVar()
        self.ping_count_var.set(self.state.get('ping_count'))
        self.extradelay_var = tk.IntVar()
        self.extradelay_var.set(self.state.get('extradelay'))
        self.leader_var = tk.IntVar()
        self.leader_var.set(self.state.get('leader'))
        self.listen_var = tk.BooleanVar()
        self.listen_var.set(self.state.get('listen'))
        self.loglevel_var = tk.IntVar()
        self.loglevel_var.set(self.state.get('loglevel'))
        self.monitor_var = tk.BooleanVar()
        self.monitor_var.set(self.state.get('monitor'))
        self.capture_var = tk.StringVar()
        #self.capture_var.set(self.state.get('capture'))
        self.playback_var = tk.StringVar()
        #self.playback_var.set(self.state.get('playback'))
        self.squelch_var = tk.IntVar()
        self.squelch_var.set(self.state.get('squelch'))
        self.trailer_var = tk.IntVar()
        self.trailer_var.set(self.state.get('trailer'))
        self.tuningrange_var = tk.IntVar()
        self.tuningrange_var.set(self.state.get('tuningrange'))
        self.use600modes_var = tk.BooleanVar()
        self.use600modes_var.set(self.state.get('use600modes'))
        self.version_var = tk.StringVar()
        #self.version_var.set(self.state.get('version'))
        self.fec_mode_var = tk.StringVar()
        self.fec_mode_var.set(self.state.get('fec_mode'))
        self.protocol_mode_var = tk.StringVar()
        self.protocol_mode_var.set(self.state.get('protocol_mode'))
        self.fec_repeats_var = tk.IntVar()
        self.fec_repeats_var.set(self.state.get('fec_repeats'))
        self.arq_dialing_quantity_var = tk.IntVar()
        self.arq_dialing_quantity_var.set(self.state.get('arq_dialing_quantity'))
        self.arqbw_var = tk.StringVar()
        self.arqbw_var.set(self.state.get('arqbw'))
        self.arqtimeout_var = tk.IntVar()
        self.arqtimeout_var.set(self.state.get('arqtimeout'))
        self.autobreak_var = tk.BooleanVar()
        self.autobreak_var.set(self.state.get('autobreak'))
        self.busyblock_var = tk.BooleanVar()
        self.busyblock_var.set(self.state.get('busyblock'))
        self.callbw_var = tk.StringVar()
        self.callbw_var.set(self.state.get('callbw'))

        self.record_command_response = False
        # initialize the ARDOPC client
        self.connect_to_ardopcf()
        #self.init_tnc() # we end up doing this in listen_for_command_responses

        self.command_listen = threading.Thread(target=self.listen_for_command_responses)
        self.command_listen.start()

        
    def arq_call(self):
        callsign = self.host_interface.get_recipients().split(',')[0]
        self.initialize_arq()
        self.cmd_response(command=f'ARQCALL {callsign} {self.state.get("arq_dialing_quantity")}')

    def ping(self):
        # to ping we need mode to be arq, listen to be true, and to have a call sign to ping
        callsign = self.host_interface.get_recipients().split(',')[0]
        self.cmd_response(command='PROTOCOLMODE ARQ')
        self.cmd_response(command=f'LISTEN {str(self.state.get("listen"))}')
        self.cmd_response(command=f'PING {callsign} {self.state.get("ping_count")}')
        # then, we just need to handle the command response which will be a PINGACK, if we get one
        # format: PINGACK SNdB Quality
        # SNdB is the signal to noise ratio in dB
        # Quality is the constellation quality of the signal, 0-100

    def initialize_arq(self):
        print("ARDOP Initializing TNC in ARQ Mode")
        self.cmd_response(command='INITIALIZE')
        self.cmd_response(command='PROTOCOLMODE ARQ')
        self.cmd_response(command=f'ARQBW {self.state.get("arqbw")}')
        self.cmd_response(command=f'ARQTIMEOUT {self.state.get("arqtimeout")}')
        self.cmd_response(command=f'AUTOBREAK {str(self.state.get("autobreak"))}')
        self.cmd_response(command=f'BUSYBLOCK {str(self.state.get("busyblock"))}')
        self.cmd_response(command=f'CALLBW {self.state.get("callbw")}')
        self.cmd_response(command=f'LISTEN {str(self.state.get("listen"))}')
        self.cmd_response(command=f'ENABLEPINGACK {str(self.state.get("enablepingack"))}')
        self.cmd_response(command=f'USE600MODES {str(self.state.get("use600modes"))}')

    def is_ready(self):
        try:
            return(self.ready.get() == "Ready")
        except RuntimeError:
            return(False)

    def is_socket_connected(self, sock):
        try:
            # Sending an empty string will not change the socket's data stream
            sock.send(b'')
            return True
        except OSError:
            return False

    def connect_to_ardopcf(self):
        # this will not stop calling itself until we are in a connected state

        try:
            self.sock_cmd.connect((self.state.get('host'), int(self.state.get('port'))))
            self.sock_cmd.setblocking(False)
            self.sock_data.connect((self.state.get('host'), int(self.state.get('port'))+1))
            self.sock_data.setblocking(False)
            time.sleep(0.1)
            self.init_tnc_fec()
            self.ready.set("Ready")
            self.ardop_status_label.config(fg='green')
        except OSError:
            if self.is_socket_connected(self.sock_cmd):
                self.sock_cmd.close()
            if self.is_socket_connected(self.sock_data):
                self.sock_data.close()
            time.sleep(0.1)
            self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            try:
                self.ready.set("Not Ready")
                self.ardop_status_label.config(fg='red')
            except RuntimeError:
                # this is a catch for the case where the plugin is being shut down without being connected
                pass
            

    def init_tnc_fec(self):
        print("ARDOP Initializing TNC in FEC Mode")
        self.cmd_response(command='INITIALIZE')
        self.cmd_response(command='PROTOCOLMODE FEC')
        self.set_tnc_settings()
        time.sleep(0.25)

    def show_help_window(self):
        help_window = tk.Toplevel()
        help_window.title("ARDOPCF Help")
        help_text = self.info + """Some data rates do not have a corresponding data rate in the datasheet.
        These will show up at 0.0m in the time to send estimate.
        """
        tk.Label(help_window, text=help_text).pack()

    def show_command_window(self):
        self.command_window = tk.Toplevel()
        self.command_window.title("ARDOPCF Command Window")
        # two text areas, the top is the history of commands and responses
        # the bottom is the command entry, much like the chat window

        self.command_history_text = tk.Text(self.command_window, height=10, width=80)
        self.command_history_text.pack()
        self.command_entry = tk.Entry(self.command_window, width=80)
        self.command_entry.pack()
        self.command_entry.bind('<Return>', self.on_command_entry)
        # destroy the window when the main window is destroyed
        self.command_window.protocol("WM_DELETE_WINDOW", self.command_window.destroy)
    
    def on_command_entry(self, event):
        command = self.command_entry.get()
        self.command_history_text.insert(tk.END, f"Sent: {command}\n")
        self.record_command_response = True
        self.cmd_response(command=command, wait=False)
        self.command_entry.delete(0, tk.END)
        self.command_history_text.see(tk.END)

    def __send_cmd(self, string: str):
        if not self.is_ready():
            return
        # Append the Carriage Return byte to the string
        try:
            string += '\r'
            self.sock_cmd.sendall(string.encode())
        except BrokenPipeError or OSError:
            self.ready.set("Not Ready")
            print("Connection to ARDOPCF lost.")
            return

    def _save_settings_to_file(self):
        with open('plugins/ardopcf_settings.json', 'w') as f:
            json.dump(self.state, f)
    
    def _load_settings_from_file(self):
        try:
            with open('plugins/ardopcf_settings.json', 'r') as f:
                self.state.update(json.load(f))
                self.set_tnc_settings()
        except FileNotFoundError:
            # on first init, we need to make sure the protocolmode is at least initialized
            # otherwise trying to send something will only load the buffer, nothing will happen
            self.on_protocol_mode_change()
        except json.JSONDecodeError:
            os.remove('plugins/ardopcf_settings.json')

    def on_settings_update(self):
        # if we changed our host/port, we need to reconnect
        if self.state['host'] != self.ardop_host_var.get() or self.state['port'] != self.ardop_port_var.get():
            self.state['host'] = self.ardop_host_var.get()
            self.state['port'] = self.ardop_port_var.get()
            self.ready.set("Not Ready")
            self.ardop_status_label.config(fg='red')
            self.connect_to_ardopcf()
        
        self.update_state_from_settings()
        
        self._save_settings_to_file()
        # If the host application change their settings, 
        if hasattr(self, 'settings_window'):
            self.settings_window.destroy()
        if not self.is_ready():
            return
        self.cmd_response(command=f'MYCALL {self.state["mycall"]}', wait=False)
        self.cmd_response(command=f'GRIDSQUARE {self.state["gridsquare"]}', wait=False)
        self.cmd_response(command=f'FECMODE {self.state["fec_mode"]}', wait=False)
        self.cmd_response(command=f'FECREPEATS {self.state["fec_repeats"]}', wait=False)

    def set_tnc_settings(self):
        for command in self.info_commands:
            if command == 'state' or command == 'buffer':
                continue # these are read only
            command = command + ' ' + str(self.state.get(command))
            self.cmd_response(command=command, wait=False)

    def query_tnc_settings(self):
        for command in self.info_commands:
            self.cmd_response(command=command, wait=False)
        self.update_state_from_settings()

    def create_settings_tab_general(self, general_tab):
        tk.Label(general_tab, text="Host").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ardop_host_entry = ttk.Entry(general_tab, textvariable=self.ardop_host_var)
        self.ardop_host_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Port").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.ardop_port_spinbox = ttk.Spinbox(general_tab, from_=0, to=65535, width=20, textvariable=self.ardop_port_var)
        self.ardop_port_spinbox.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="My Call").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.mycall_entry = ttk.Entry(general_tab, textvariable=self.mycall_var)
        self.mycall_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="My Aux").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.myaux_entry = ttk.Entry(general_tab, textvariable=self.myaux_var)
        self.myaux_entry.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Grid Square").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.gridsquare_entry = ttk.Entry(general_tab, textvariable=self.gridsquare_var)
        self.gridsquare_entry.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)

        self.busydet_entry = ttk.Checkbutton(general_tab, text="Busy Detection", variable=self.busydet_var)
        self.busydet_entry.grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)

        tk.Label(general_tab, text="Drive Level").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.drivelevel_entry = ttk.Spinbox(general_tab, from_=0, to=100, width=20, textvariable=self.drivelevel_var)
        self.drivelevel_entry.grid(row=6, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="CW ID").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        self.cwid_entry = ttk.OptionMenu(general_tab, self.cwid_var, 'TRUE', 'ONOFF', 'FALSE')
        self.cwid_entry.grid(row=7, column=1, sticky=tk.EW, padx=5, pady=5)

        self.enablepingack_entry = ttk.Checkbutton(general_tab, text="Enable Ping Ack", variable=self.enablepingack_var)
        self.enablepingack_entry.grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)

        tk.Label(general_tab, text="Ping Count").grid(row=9, column=0, sticky=tk.W, padx=5, pady=5)
        self.ping_count_entry = ttk.Spinbox(general_tab, from_=1, to=15, width=20, textvariable=self.ping_count_var)
        self.ping_count_entry.grid(row=9, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Extra Delay").grid(row=10, column=0, sticky=tk.W, padx=5, pady=5)
        self.extradelay_entry = ttk.Spinbox(general_tab, from_=0, to=100000, width=20, textvariable=self.extradelay_var)
        self.extradelay_entry.grid(row=10, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Leader length").grid(row=11, column=0, sticky=tk.W, padx=5, pady=5)
        self.leader_entry = ttk.Spinbox(general_tab, from_=120, to=2500, width=20, textvariable=self.leader_var)
        self.leader_entry.grid(row=11, column=1, sticky=tk.EW, padx=5, pady=5)

        self.listen_entry = ttk.Checkbutton(general_tab, text="Listen", variable=self.listen_var)
        self.listen_entry.grid(row=12, column=0, sticky=tk.W, padx=5, pady=5)

        tk.Label(general_tab, text="Log Level").grid(row=13, column=0, sticky=tk.W, padx=5, pady=5)
        self.loglevel_entry = ttk.Spinbox(general_tab, from_=0, to=8, width=20, textvariable=self.loglevel_var)
        self.loglevel_entry.grid(row=13, column=1, sticky=tk.EW, padx=5, pady=5)

        self.monitor_entry = ttk.Checkbutton(general_tab, text="Monitor", variable=self.monitor_var)
        self.monitor_entry.grid(row=14, column=0, sticky=tk.W, padx=5, pady=5)

        tk.Label(general_tab, text="Capture Device").grid(row=15, column=0, sticky=tk.W, padx=5, pady=5)
        self.capture_entry = ttk.Entry(general_tab, textvariable=self.capture_var)
        self.capture_entry.grid(row=15, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Playback Device").grid(row=16, column=0, sticky=tk.W, padx=5, pady=5)
        self.playback_entry = ttk.Entry(general_tab, textvariable=self.playback_var)
        self.playback_entry.grid(row=16, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Squelch").grid(row=17, column=0, sticky=tk.W, padx=5, pady=5)
        self.squelch_entry = ttk.Spinbox(general_tab, from_=1, to=10, width=20, textvariable=self.squelch_var)
        self.squelch_entry.grid(row=17, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Trailer Length").grid(row=18, column=0, sticky=tk.W, padx=5, pady=5)
        self.trailer_entry = ttk.Spinbox(general_tab, from_=0, to=200, width=20, textvariable=self.trailer_var)
        self.trailer_entry.grid(row=18, column=1, sticky=tk.EW, padx=5, pady=5)

        tk.Label(general_tab, text="Tuning Range").grid(row=19, column=0, sticky=tk.W, padx=5, pady=5)
        self.tuningrange_entry = ttk.Spinbox(general_tab, from_=0, to=200, width=20, textvariable=self.tuningrange_var)
        self.tuningrange_entry.grid(row=19, column=1, sticky=tk.EW, padx=5, pady=5)

        self.use600modes_entry = ttk.Checkbutton(general_tab, text="Use 600 Modes", variable=self.use600modes_var)
        self.use600modes_entry.grid(row=20, column=0, sticky=tk.W, padx=5, pady=5)

        tk.Label(general_tab, text="Version").grid(row=21, column=0, sticky=tk.W, padx=5, pady=5)
        self.version_entry = ttk.Entry(general_tab, textvariable=self.version_var)
        self.version_entry.grid(row=21, column=1, sticky=tk.EW, padx=5, pady=5)

        general_tab.columnconfigure(1, weight=1)
        

    def create_settings_tab_fec(self, fec_tab):
        tk.Label(fec_tab, text="FEC Mode").pack()
        
        self.fec_mode_menu = tk.OptionMenu(fec_tab, self.fec_mode_var, *self.fec_modes)
        self.fec_mode_var.set(self.state['fec_mode'])
        self.fec_mode_menu.pack()

        tk.Label(fec_tab, text="FEC Repeats").pack()
        self.fec_repeats_scale = tk.Scale(fec_tab, from_=0, to=5, orient=tk.HORIZONTAL, variable=self.fec_repeats_var)
        self.fec_repeats_var.set(self.state['fec_repeats'])
        self.fec_repeats_scale.pack()

    def create_settings_tab_arq(self, arq_tab):
        # ARQ Dialing Quantity
        ttk.Label(arq_tab, text="Dialing Attempts:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.arq_dialing_quantity_spinbox = ttk.Spinbox(arq_tab, from_=2, to=15, width=20, textvariable=self.arq_dialing_quantity_var)
        self.arq_dialing_quantity_spinbox.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        # ARQ Bandwidth
        ttk.Label(arq_tab, text="ARQ Bandwidth:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.arq_bw_menu = tk.OptionMenu(arq_tab, self.arqbw_var, *self.arq_bw_modes)
        self.arqbw_var.set(self.state['arqbw'])
        self.arq_bw_menu.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        # ARQ Timeout
        ttk.Label(arq_tab, text="ARQ Timeout:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.arqtimeout_entry = ttk.Spinbox(arq_tab, from_=30, to=240, width=20, textvariable=self.arqtimeout_var)
        self.arqtimeout_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)

        # Auto Break
        #self.autobreak_check = ttk.Checkbutton(arq_tab, text="Auto Break", variable=self.autobreak_var)
        #self.autobreak_check.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)

        # Busy Block
        self.busyblock_check = ttk.Checkbutton(arq_tab, text="Busy Block", variable=self.busyblock_var)
        self.busyblock_check.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)

        # Call Bandwidth (needs developer review, what does this actually do in ardopcf?)
        #ttk.Label(arq_tab, text="Call Bandwidth:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        #self.callbw_entry = ttk.OptionMenu(arq_tab, self.callbw_var, *self.arq_bw_modes)
        #self.callbw_entry.grid(row=5, column=1, sticky=tk.EW, padx=5, pady=5)
        arq_tab.columnconfigure(1, weight=1)

    def create_settings_menu(self):
        '''This is called whenever this plugin's settings button is clicked. It should create
        a new window with the settings for this plugin.'''
        self.query_tnc_settings()
        self.update_tk_vars()
        self.settings_window = tk.Toplevel()
        self.settings_window.title("ARDOPCF Settings")
        topframe = tk.Frame(self.settings_window)
        topframe.pack(side=tk.TOP)

        # add a tabbed interface for the settings
        tabcontrol = ttk.Notebook(topframe)
        tabcontrol.pack(expand=True, fill='x')

        general_tab = tk.Frame(tabcontrol)
        fec_tab = tk.Frame(tabcontrol)
        arq_tab = tk.Frame(tabcontrol)

        tabcontrol.add(general_tab, text="General")
        tabcontrol.add(fec_tab, text="FEC")
        tabcontrol.add(arq_tab, text="ARQ")

        # tk.Label(general_tab, text="Host").pack()
        # self.ardop_host_entry = tk.Entry(general_tab, textvariable=self.ardop_host_var)
        # self.ardop_host_entry.pack()
        # tk.Label(general_tab, text="Port").pack()
        # self.ardop_port_spinbox = tk.Spinbox(general_tab, from_=0, to=65535, width=20, textvariable=self.ardop_port_var)
        # self.ardop_port_spinbox.pack()

        self.create_settings_tab_general(general_tab)
        self.create_settings_tab_fec(fec_tab)
        self.create_settings_tab_arq(arq_tab)

        buttonframe = tk.Frame(self.settings_window)
        buttonframe.pack(side=tk.BOTTOM)

        help_button = tk.Button(buttonframe, text="Help", command=self.show_help_window)
        help_button.pack(side=tk.LEFT)

        # command window button
        command_button = tk.Button(buttonframe, text="Command Window", command=self.show_command_window)
        command_button.pack(side=tk.LEFT)

        self.save_button = tk.Button(buttonframe, text="Save", command=self.on_settings_update)
        self.save_button.bind('<Return>', self.on_settings_update)
        self.save_button.pack(side=tk.BOTTOM)
        # save settings when we close the window as well
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_update)

    def on_protocol_mode_change(self, *args):
        self.state['protocolmode'] = self.protocolmode_var.get()
        if self.state['protocolmode'] == 'FEC':
            self.init_tnc_fec()
        elif self.state['protocolmode'] == 'ARQ':
            self.initialize_arq()
        else:
            pass

    def create_plugin_frame(self, tkParent):
        ardop_frame = tk.Frame(tkParent)
        statusframe = tk.Frame(ardop_frame)
        statusframe.pack()
        ardop_label = tk.Label(statusframe, text=self.definition['name'])
        ardop_label.pack(side=tk.LEFT)
        self.ardop_status_label = tk.Label(statusframe, textvariable=self.ready)
        self.ardop_status_label.pack(side=tk.RIGHT)
        if self.is_ready():
            self.ready.set("Ready")
            self.ardop_status_label.config(fg='green')
        protocol_label = tk.Label(ardop_frame, text="Protocol Mode")
        protocol_label.pack()
        protocolmode_selector = tk.OptionMenu(ardop_frame, self.protocolmode_var, 'FEC', 'ARQ', 'RXO', command=self.on_protocol_mode_change)
        protocolmode_selector.pack()
        ping_button = tk.Button(ardop_frame, text="Ping", command=self.ping)
        ping_button.pack()
        ardop_button = tk.Button(ardop_frame, text="Configure", command=self.create_settings_menu)
        ardop_button.pack(side=tk.BOTTOM)
        self.clear_buffer_button = tk.Button(ardop_frame, text="Stop/Clear Buffer", command=self.on_clear_buffer)
        self.clear_buffer_button.pack(side=tk.BOTTOM)
        ardop_frame.pack()

    def on_ui_transport_status_frame(self, tkParent: tk.Frame):
        status_text = self.state.get('state')
        status_text += f" | BUFFER:{self.state.get('buffer')}"
        status_text += f" | TTS: {self.estimate_time_to_send()}m "
        status_text += f"@ {self.state.get('fec_mode')}"

        if not self.is_ready():
            status_text = "Not Connected"

        self.transport_status_frame_text.set(status_text)

        # check if a tk.Frame has already been created and exists
        # in the tkParent.
        if tkParent.winfo_children():
            for child in tkParent.winfo_children():
                if child == self.status_frame:
                    pass
        else:
            self.status_frame = tk.Frame(tkParent)
            label = tk.Label(self.status_frame, text="ARDOP Status")
            label.pack()
            status = tk.Label(self.status_frame, textvariable=self.transport_status_frame_text)
            status.pack()
            self.status_frame.pack()

    def on_transport_state_update(self):
        # logic to bug tnc for state updates
        self.cmd_response(command='STATE', wait=False)
        self.cmd_response(command='BUFFER', wait=False)

    def append_bytes_to_buffer(self, data : bytes):
        # ARDOPCF is a single-threaded application, and it spends most of
        # its time processing incoming audio to decode for frames.
        # Because of this, it doesn't immediately intake new data or commands from their sockets,
        # or immediately issue a response to commands. Because of this, we need to wait
        # in between things we want to send. Often, plugins will send data to the buffer,
        # another plugin may send data to the buffer, and the TNC will not have processed
        # the first data before the second data is loaded. A message may sit in the
        # outgoing buffer until a new message is loaded and sent.
        
        # you CANNOT sleep in any loops here.

        if not self.is_ready():
            return
        if not data:
            return
    

        # if the data is too long, we can't send it without splitting it up
        # 1000 byte chunks seems comfortable. Every 1000 bytes seem to take about 200ms to load
        est_rate = (len(data) / 1000) * 1.5
        reasonable_timeout_value = int(est_rate) if int(est_rate) > 2 else 2
        for i in range(0, len(data), 1000):
            data_chunk = data[i:i+1000]
            # data format is <2 bytes for length><data>
            # data should already come here with the hamChat standard header
            data_length = len(data_chunk).to_bytes(2, 'big')
            data_chunk = data_length + data_chunk
            self.sock_data.sendall(data_chunk)

        # wait until the TNC reports the buffer size that we tried to load
        load_timeout = 0
        while self.state.get('buffer') < len(data):
            time.sleep(0.2)
            load_timeout += 1
            buff_report = self.cmd_response(command='BUFFER', wait=True) # Warning: this has possibility to make us miss a PTT command
            if len(buff_report.split(' ')) > 1:
                try:
                    self.state['buffer'] = int(buff_report.split(' ')[1])
                except ValueError:
                    pass # we keep competing for time with the socket. Need to find a better way.
            
            if load_timeout > reasonable_timeout_value:
                print(f"ARDOP Buffer Load Timeout (tried loading {len(data)} bytes, got {self.state.get('buffer')} bytes)")
                break

        if self.host_interface.debug.get():
            print(f"ARDOP Buffer Ready: {self.state.get('buffer')} bytes.")

    def on_transmit_buffer(self):
        if self.state['protocol_mode'] == 'ARQ':
            self.arq_call()
        elif self.state['protocol_mode'] == 'FEC':
            self.cmd_response(command='FECSEND TRUE', wait=False)
        else:
            pass

    def on_clear_buffer(self):
        self.cmd_response(command='PURGEBUFFER', wait=False)

    def estimate_time_to_send(self, datalen: int = 0) -> float:
        # this is a helper function to estimate the time it will take to send a message
        # this is a rough estimate, and will not be accurate for messages that are not
        # a multiple of 1000 bytes
        if not datalen:
            datalen = int(self.state.get("buffer"))
        if not self.is_ready():
            return(0.0)
        current_mode = self.state.get('fec_mode')
        data_rate = self.rate_table.get(current_mode)
        if not data_rate:
            return(0.0)
        # round to one decimal place
        result = round((datalen / data_rate), 1)
        
        return(result)

    def on_get_data(self) -> bytes:
        # This is blocking, and should run in its own thread or migrate everything to asyncio

        # This will return ONE set of frames from the TNC, marked by the :END: footer
        # or until we see another FEC/ARQ/ERR prefix, which means we have another data packet,

        # the smallest data frame 4FSK.200.50S will encode just 16 data bytes
        # chances are that we will not receive a full frame in one go unless 
        # we are using a high data rate

        # no matter what frame we recieved, or the order we got the frame
        # we will always get the following bytes from the beginning of the data socket:
        # 2 bytes for the length of the frame
        # 3 bytes for the prefix if not the first frame of a series of frames

        # we can detect if the message is over by checking if the end of the message is ':END:'
        # or if we simply stop getting data from the socket.

        # example received data: b'K7OTR-1:chat:0.1:K7OTR:BEGIN:A much longer message, here it i\x00CFECs, here it is here it is, multiple farames fefjensfnrsribghilerb\x00\x0eFECrghbgr:END:'

        # possibly an ARDOP bug here that thinks frames are duplicate when they're not: https://vscode.dev/github/Dinsmoor/ardopcf/blob/develop/ARDOPC/FEC.c#L363

        if not self.is_ready():
            return(None)
        data = b''
        while not self.stop_event.is_set():
            try:
                # The first two bytes should be the length of the individually decoded frame
                # this may break if our buffer has an incomplete frame for us, or the
                # sending station has an incomplete frame in their buffer.
                length = self.sock_data.recv(2)
                if not length:
                    # if we get nothing, we can break
                    break
                length = int.from_bytes(length, 'big')
                # get the rest of this data frame
                this_frame = self.sock_data.recv(length) # https://github.com/Dinsmoor/ardopcf/blob/eab1f3165a30a0a40221a20b54f5fa1d099c2482/src/common/TCPHostInterface.c#L253-L254
                if self.host_interface.debug.get():
                    print(f"ARDOPCF: Incoming Frame: len:{length} data:{this_frame}")
                # remove the prefix if it exists (we don't need it yet in this application)
                
                if this_frame[:3] == b'FEC':
                    this_frame = this_frame[3:]
                elif this_frame[:3] == b'ARQ':
                    this_frame = this_frame[3:]
                elif this_frame[:3] == b'ERR':
                    # discard error frames, we don't use them yet
                    if self.host_interface.debug.get():
                        print(f"ARDOPCF: Error Frame: {this_frame}")
                    this_frame = b''
                    continue
                
                if self.host_interface.debug.get():
                    print(f"ARDOPCF: Frame: {this_frame}")
                data += this_frame
                # if we encounter the end of the message, we can break,
                # and save the rest for another iteration (ardop may group messages into one frame)
                if b':END:' in data[-5:]:
                    break
            except BlockingIOError:
                # This will happen if we try to read from the socket and there is no data
                # Completely normal behavior, we just need to wait a moment if there is any additional data
                time.sleep(0.2)
                continue
            except OSError:
                # we may have a broken pipe, or a timeout
                # either way, we need to reconnect to the TNC
                # before trying again.
                time.sleep(0.1)
                break
            except Exception as e:
                print(f"ARDOPCF: Unexpected Error: {e}")
                break
        return(data)

    def abort(self):
        # abort actually sucks and doesn't work immediately
        # it's better to clear the buffer with PURGEBUFFER,
        # this makes the TNC stop transmitting, much better than ABORT
        self.cmd_response(command="ABORT", wait=False)

    def cmd_response(self, command=None, wait=False) -> str:
        # this does not play nice with anything.
        # If I were smarter, I would have done this a different way.
        # The main limitation is PTT control from ardop being time sensitive. (<50ms)
        # If it weren't for that, everything would be so much easier.
        if not self.is_ready():
            return(None)

        if command:
            #if self.host_interface.debug.get():
            #    print(f"ARDOP CMD: {command}")
            self.__send_cmd(command)
            
        if not wait:
            return(None)

        line = b''
        while not self.stop_event.is_set():
            try:
                part = self.sock_cmd.recv(1)
                if part != b"\r":
                    line+=part
                elif part == b"\r":
                    break
            except BlockingIOError as e:
                # this is normal, since we set the socket to non-blocking
                # mode to be able to terminate upon stop_event
                # we wait a short time to not hog the CPU if there's no data to read
                time.sleep(0.01)
                continue
            except OSError as e:
                # might be a broken pipe, or a timeout
                # either way, we need to reconnect
                return(None)
            # if we get here, we should be reading as fast as possible
        return line.decode()
    

    def update_state_from_settings(self):
        self.state['host'] = self.ardop_host_var.get()
        self.state['port'] = self.ardop_port_var.get()
        self.state['mycall'] = self.mycall_var.get()
        self.state['gridsquare'] = self.gridsquare_var.get()
        self.state['busydet'] = self.busydet_var.get()
        self.state['drivelevel'] = self.drivelevel_var.get()
        self.state['cwid'] = self.cwid_var.get()
        self.state['enablepingack'] = self.enablepingack_var.get()
        self.state['ping_count'] = self.ping_count_var.get()
        self.state['extradelay'] = self.extradelay_var.get()
        self.state['leader'] = self.leader_var.get()
        self.state['listen'] = self.listen_var.get()
        self.state['loglevel'] = self.loglevel_var.get()
        self.state['monitor'] = self.monitor_var.get()
        #self.state['capture'] = self.capture_var.get()
        #self.state['playback'] = self.playback_var.get()
        self.state['squelch'] = self.squelch_var.get()
        self.state['trailer'] = self.trailer_var.get()
        self.state['tuningrange'] = self.tuningrange_var.get()
        self.state['use600modes'] = self.use600modes_var.get()
        #self.state['version'] = self.version_var.get()
        self.state['fec_mode'] = self.fec_mode_var.get()
        self.state['fec_repeats'] = self.fec_repeats_var.get()
        self.state['arq_dialing_quantity'] = self.arq_dialing_quantity_var.get()
        self.state['arqbw'] = self.arqbw_var.get()
        self.state['arqtimeout'] = self.arqtimeout_var.get()
        self.state['autobreak'] = self.autobreak_var.get()
        self.state['busyblock'] = self.busyblock_var.get()
        self.state['callbw'] = self.callbw_var.get()


    def update_tk_vars(self):
        self.mycall_var.set(self.state['mycall'])
        self.gridsquare_var.set(self.state['gridsquare'])
        self.busydet_var.set(self.state['busydet'])
        self.drivelevel_var.set(self.state['drivelevel'])
        self.cwid_var.set(self.state['cwid'])
        self.enablepingack_var.set(self.state['enablepingack'])
        self.ping_count_var.set(self.state['ping_count'])
        self.extradelay_var.set(self.state['extradelay'])
        self.leader_var.set(self.state['leader'])
        self.listen_var.set(self.state['listen'])
        self.loglevel_var.set(self.state['loglevel'])
        self.monitor_var.set(self.state['monitor'])
        self.capture_var.set(self.state['capture'])
        self.playback_var.set(self.state['playback'])
        self.squelch_var.set(self.state['squelch'])
        self.trailer_var.set(self.state['trailer'])
        self.tuningrange_var.set(self.state['tuningrange'])
        self.use600modes_var.set(self.state['use600modes'])
        self.version_var.set(self.state['version'])
        self.fec_mode_var.set(self.state['fec_mode'])
        self.fec_repeats_var.set(self.state['fec_repeats'])
        self.arq_dialing_quantity_var.set(self.state['arq_dialing_quantity'])
        self.arqbw_var.set(self.state['arqbw'])
        self.arqtimeout_var.set(self.state['arqtimeout'])
        self.autobreak_var.set(self.state['autobreak'])
        self.busyblock_var.set(self.state['busyblock'])
        self.callbw_var.set(self.state['callbw'])


    def listen_for_command_responses(self):
        # this is our main event loop for handling command responses from the TNC
        # wherever we send a command in this code, here is were we will asynchronously
        # parse and handle the response.
        while not self.stop_event.is_set():
            debug = self.host_interface.debug.get()
            if not self.is_ready():
                if debug:
                    print("ARDOP Not ready, reconnecting.")
                # try to reconnect to the TNC
                self.connect_to_ardopcf()
                continue
            response = self.cmd_response(wait=True)
            self.command_response_history.append(response)

            try:
                for entry in self.command_response_history:
                    if ('PTT TRUE' in entry):
                        self.state['ptt'] = True
                        self.host_interface.plugMgr.on_key_transmitter()
                    elif ('PTT FALSE' in entry):
                        self.state['ptt'] = False
                        self.host_interface.plugMgr.on_unkey_transmitter()
                    elif entry.startswith('MYCALL'):
                        self.state['mycall'] = entry.split()[-1]
                    elif entry.startswith('MYAUX'):
                        if len(entry.split()) > 1:
                            self.state['myaux'] = entry.split()[-1]
                    elif entry.startswith('PURGEBUFFER'):
                        pass
                    elif entry.startswith('GRIDSQUARE'):
                        self.state['gridsquare'] = entry.split()[-1]
                    elif entry.startswith('BUFFER'):
                        self.state['buffer'] = int(entry.split()[-1])
                    elif entry.startswith('STATE'):
                        self.state['state'] = entry.split()[-1]
                    elif entry.startswith('FECSEND'):
                        pass
                    elif entry.startswith('PROTOCOLMODE'):
                        self.state['protocol_mode'] = entry.split()[-1]
                    elif entry.startswith('PING'):
                        self.host_interface.print_to_chatwindow(entry)
                    elif entry.startswith('PINGACK'):
                        self.host_interface.print_to_chatwindow(entry)
                    elif entry.startswith('FECMODE'):
                        self.state['fec_mode'] = entry.split()[-1]
                    elif entry.startswith('FECREPEATS'):
                        self.state['fec_repeats'] = int(entry.split()[-1])
                    elif entry.startswith('LISTEN'):
                        self.state['listen'] = entry.split()[-1]
                    elif entry.startswith('ENABLEPINGACK'):
                        self.state['enablepingack'] = entry.split()[-1]
                    elif entry.startswith('USE600MODES'):
                        #FIXME this does not properly set the use600modes variable
                        if entry.split()[-1] == 'FALSE':
                            self.state['use600modes'] = False
                        else:
                            self.state['use600modes'] = True
                    elif entry.startswith('VERSION'):
                        self.state['version'] = entry.split()[-1]
                    elif entry.startswith('LOGLEVEL'):
                        self.state['loglevel'] = int(entry.split()[-1])
                    elif entry.startswith('MONITOR'):
                        self.state['monitor'] = entry.split()[-1]
                    elif entry.startswith('CAPTURE'):
                        self.state['capture'] = entry.split()[-1]
                    elif entry.startswith('PLAYBACK'):
                        self.state['playback'] = entry.split()[-1]
                    elif entry.startswith('SQUELCH'):
                        self.state['squelch'] = int(entry.split()[-1])
                    elif entry.startswith('TRAILER'):
                        self.state['trailer'] = int(entry.split()[-1])
                    elif entry.startswith('TUNINGRANGE'):
                        self.state['tuningrange'] = int(entry.split()[-1])
                    elif entry.startswith('EXTRADELAY'):
                        self.state['extradelay'] = int(entry.split()[-1])
                    elif entry.startswith('LEADER'):
                        self.state['leader'] = int(entry.split()[-1])
                    elif entry.startswith('BUSYDET'):
                        self.state['busydet'] = entry.split()[-1]
                    elif entry.startswith('DRIVELEVEL'):
                        self.state['drivelevel'] = entry.split()[-1]
                    elif entry.startswith('CWID'):
                        self.state['cwid'] = entry.split()[-1]
                    elif entry.startswith('ARQBW'):
                        self.state['arqbw'] = entry.split()[-1]
                    elif entry.startswith('ARQTIMEOUT'):
                        self.state['arqtimeout'] = int(entry.split()[-1])
                    elif entry.startswith('AUTOBREAK'):
                        self.state['autobreak'] = entry.split()[-1]
                    elif entry.startswith('BUSYBLOCK'):
                        self.state['busyblock'] = entry.split()[-1]
                    elif entry.startswith('CALLBW'):
                        self.state['callbw'] = entry.split()[-1]
                    elif entry.startswith('INITIALIZE'):
                        pass
                    else:
                        pass
                        #self.host_interface.print_to_chatwindow(entry)
                    if debug:
                        if not entry.startswith('BUFFER'):
                            if not entry.startswith('STATE'):
                                print(f"ARDOPCF: {entry}")
                    try:
                        if hasattr(self, 'command_history_text') and self.command_history_text.winfo_exists():
                            if self.record_command_response:
                                self.command_history_text.insert(tk.END, f"{entry}\n")
                                self.record_command_response = False
                    except RuntimeError:
                        # this is a catch for the case where the command_history_text is None
                        # usually at program termination
                        pass
                    self.command_response_history.remove(entry)
                    # plugins might really interfere with this thread, it may be better
                    # to spawn a thread when this is called. Will test and change as needed.
                    #self.host_interface.plugMgr.on_command_received(entry)
            except TypeError:
                # this is a catch for the case where the command_response_history is None
                # usually at program termination or on timeout
                pass
        print('ARDOPCF Command Response Thread Exiting')

    def IPC(self, target_plugin: str, from_plugin: str, command: str, data: bytes = None) -> dict:
        if target_plugin != self.definition['name']:
            return({})
        if command == 'send':
            self.append_bytes_to_buffer(data)
            self.on_transmit_buffer()


    def on_shutdown(self):
        self.stop_event.set()
        # this is a hack to get the command_response thread to exit
        # (it's blocking on a recv call until it gets a response from the TNC)
        if self.is_ready():
            self.cmd_response(command='ABORT', wait=False)
            self.cmd_response(command='STATE', wait=False)
            self.sock_cmd.close()
            self.sock_data.close()
