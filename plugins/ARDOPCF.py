import socket
import select
import time
import threading
import sys
import tkinter as tk
import json
from hamChatPlugin import hamChatPlugin


class ARDOPCF(hamChatPlugin):
    def __init__(self, host_interface):
        self.info = """
        This plugin interfaces with the ARDOPC TNC to provide ARDOP transport for hamChat.
        Make sure ardopcf is running on localhost on ports 8515 and 8516.
        ex. ./ardopcf 8515 plughw:1,0 plughw:1,0
        Get ARDOPCF here: https://github.com/pflarue/ardop
        """
        self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.stop_event = threading.Event()
        self.data_transfer_complete = threading.Event()
        self.command_response_history = []
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

        self.state = {
            'state': 'DISC',
            'buffer': 0,
            'ptt': False,
            'mycall': 'N0CALL',
            'gridsquare': 'AA00AA',
            'fec_mode': '4FSK.200.50S',
            'protocol_mode': 'FEC',
            'fec_repeats': 0,
            'host': 'localhost',
            'port': 8515

        }
        self._load_settings_from_file()

        self.ardop_host_var = tk.StringVar()
        self.ardop_port_var = tk.IntVar()
        self.ardop_host_var.set(self.state.get('host'))
        self.ardop_port_var.set(self.state.get('port'))

        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'ARDOPCF',
            'version': 0.1,
            'description': self.info,
            'transport': 'ARDOP',
            'handlers': [],
            'protocol_fields': [],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
        # initialize the ARDOPC client
        self.connect_to_ardopcf()
        #self.init_tnc() # we end up doing this in listen_for_command_responses
        self.fec_mode_var = tk.StringVar()
        self.fec_mode_var.set(self.state.get('fec_mode'))
        self.fec_repeats_var = tk.IntVar()
        self.fec_repeats_var.set(self.state.get('fec_repeats'))

        self.command_listen = threading.Thread(target=self.listen_for_command_responses)
        self.command_listen.start()

    def is_ready(self):
        return(self.ready.get() == "Ready")

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
            self.sock_data.connect((self.state.get('host'), int(self.state.get('port'))+1))
            self.init_tnc()
            self.ready.set("Ready")
            self.ardop_status_label.config(fg='green')
        except OSError:
            if self.is_socket_connected(self.sock_cmd):
                self.sock_cmd.close()
            if self.is_socket_connected(self.sock_data):
                self.sock_data.close()
            time.sleep(0.25)
            self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ready.set("Not Ready")
            self.ardop_status_label.config(fg='red')

            # call this function again to try to reconnect
            self.connect_to_ardopcf()
            

    def init_tnc(self):
        self.cmd_response(command='INITIALIZE')
        self.cmd_response(command=f'MYCALL {self.state.get("mycall")}')
        self.cmd_response(command=f'GRIDSQUARE {self.state.get("gridsquare")}')
        self.cmd_response(command='PROTOCOLMODE FEC')
        self.cmd_response(command=f'FECMODE {self.state.get("fec_mode")}')
        self.cmd_response(command=f'FECREPEATS {self.state.get("fec_repeats")}')
        self.cmd_response(command='FECID 1')
        self.cmd_response(command='LISTEN 1')
        self.cmd_response(command='ENABLEPINGACK 1')
        self.cmd_response(command='USE600MODES 1') # symbol rate violation if on HF >:^)
        time.sleep(0.25)

    def show_help_window(self):
        help_window = tk.Toplevel()
        help_window.title("ARDOPCF Help")
        help_text = self.info + """Some data rates do not have a corresponding data rate in the datasheet.
        These will show up at 0.0m in the time to send estimate.
        """
        tk.Label(help_window, text=help_text).pack()

    def __send_cmd(self, string: str):
        if not self.is_ready():
            return
        # Append the Carriage Return byte to the string
        try:
            string += '\r'
            self.sock_cmd.sendall(string.encode())
        except BrokenPipeError or OSError:
            self.ready.set("Not Ready")
            print("Connection to ARDOPC client lost.")
            return

    def _save_settings_to_file(self):
        with open('plugins/ardopcf_settings.json', 'w') as f:
            json.dump(self.state, f)
    
    def _load_settings_from_file(self):
        try:
            with open('plugins/ardopcf_settings.json', 'r') as f:
                self.state.update(json.load(f))
        except FileNotFoundError:
            pass

    def on_settings_update(self):
        self.state['mycall'] = self.host_interface.settings['callsign']
        self.state['gridsquare'] = self.host_interface.settings['gridsquare']
        self.state['fec_mode'] = self.fec_mode_var.get()
        self.state['fec_repeats'] = self.fec_repeats_var.get()
        # if we changed our host/port, we need to reconnect
        if self.state['host'] != self.ardop_host_var.get() or self.state['port'] != self.ardop_port_var.get():
            self.state['host'] = self.ardop_host_var.get()
            self.state['port'] = self.ardop_port_var.get()
            self.ready.set("Not Ready")
            self.ardop_status_label.config(fg='red')
            self.connect_to_ardopcf()
        
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
        
    def create_settings_menu(self):
        '''This is called whenever this plugin's settings button is clicked. It should create
        a new window with the settings for this plugin.'''
        self.settings_window = tk.Toplevel()
        self.settings_window.title("ARDOPCF Settings")
        topframe = tk.Frame(self.settings_window)
        topframe.pack(side=tk.TOP)

        self.ardop_connection_frame = tk.Frame(topframe)
        tk.Label(self.ardop_connection_frame, text="Host").pack()
        self.ardop_host_entry = tk.Entry(self.ardop_connection_frame, textvariable=self.ardop_host_var)
        self.ardop_host_entry.pack()
        tk.Label(self.ardop_connection_frame, text="Port").pack()
        self.ardop_port_spinbox = tk.Spinbox(self.ardop_connection_frame, from_=0, to=65535, width=20, textvariable=self.ardop_port_var)
        self.ardop_port_spinbox.pack()
        self.ardop_connection_frame.pack(side=tk.LEFT)

        self.ardopsettings_frame = tk.Frame(topframe)
        tk.Label(self.ardopsettings_frame, text="FEC Mode").pack()
        
        self.fec_mode_menu = tk.OptionMenu(self.ardopsettings_frame, self.fec_mode_var, *self.fec_modes)
        self.fec_mode_var.set(self.state['fec_mode'])
        self.fec_mode_menu.pack()

        tk.Label(self.ardopsettings_frame, text="FEC Repeats").pack()
        self.fec_repeats_scale = tk.Scale(self.ardopsettings_frame, from_=0, to=5, orient=tk.HORIZONTAL, variable=self.fec_repeats_var)
        self.fec_repeats_var.set(self.state['fec_repeats'])
        self.fec_repeats_scale.pack()
        self.ardopsettings_frame.pack(side=tk.RIGHT)

        buttonframe = tk.Frame(self.settings_window)
        buttonframe.pack(side=tk.BOTTOM)

        help_button = tk.Button(buttonframe, text="Help", command=self.show_help_window)
        help_button.pack(side=tk.LEFT)

        self.save_button = tk.Button(buttonframe, text="Save", command=self.on_settings_update)
        self.save_button.bind('<Return>', self.on_settings_update)
        self.save_button.pack(side=tk.BOTTOM)

    def create_plugin_frame(self, tkParent):
        ardop_frame = tk.Frame(tkParent)
        statusframe = tk.Frame(ardop_frame)
        statusframe.pack()
        ardop_label = tk.Label(statusframe, text=self.definition['name'])
        ardop_label.pack(side=tk.LEFT)
        self.ardop_status_label = tk.Label(statusframe, textvariable=self.ready)
        self.ardop_status_label.pack(side=tk.RIGHT)
        if self.is_ready():
            self.ardop_status_label.config(fg='green')
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

    def send_text_to_buffer(self, message : str):
        if not self.is_ready():
            return
        # this application only uses FEC mode (for now)
        # data format is <2 bytes for length><FEQ or ARQ><data>
        data = 'FEC' + message
        if len(data) > 1000:
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

    def append_bytes_to_buffer(self, data : bytes):
        if not self.is_ready():
            return
        # this application only uses FEC mode
        # data format is <2 bytes for length><FEQ or ARQ><data>
        # data should already come here with the protocol header

        # if the data is too long, we can't send it without splitting it up
        # 1000 seems comfortable.

        for i in range(0, len(data), 1000):
            data_chunk = data[i:i+1000]
            # every chunk of data needs to be prefixed with the FEC prefix else the TNC will ignore it
            data_chunk = b'FEC' + data_chunk
            data_length = len(data_chunk).to_bytes(2, 'big')
            data_chunk = data_length + data_chunk
            self.sock_data.sendall(data_chunk)

    def on_transmit_buffer(self):
        # twice! because the TNC is a little finicky on first transmit
        self.cmd_response(command='FECSEND TRUE', wait=False)
        self.cmd_response(command='FECSEND TRUE', wait=False)
        # TODO: make this play nice with other transport plugins
        self.host_interface.entry['state'] = 'normal'

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
        # This is blocking, and should run in its own thread 
        # It will wait until it gets a full set of frames, or the transmission
        # times out. The timeout is 7 seconds, which might be enough for a few frame repeats,
        # if the sender has repeats enabled

        # the smallest data frame 4FSK.200.50S will encode just 16 data bytes
        # chances are that we will not receive a full frame in one go unless 
        # we are using a high data rate

        # no matter what frame we recieved, or the order we got the frame
        # we will always get the following bytes from the beginning of the data socket:
        # 2 bytes for the length of the frame
        # 6 bytes for the FECFEC prefix if the first frame of a series of frames (bug?)
        # 3 bytes for the FEC prefix if not the first frame of a series of frames

        # we can detect if the message is over by checking if the end of the message is ':END:'

        all_frame_data = b''
        timeout = 7
        listen_time = 0.1
        start_time = time.time()

        while not self.stop_event.is_set():
            # no data for a while? give up
            if time.time() - start_time > timeout:
                break
            if not self.is_ready():
                self.connect_to_ardopcf()
                
            # check every 300ms if we have data (time delay between frames or repeats)
            if self.sock_data in select.select([self.sock_data], [], [], listen_time)[0]:
                raw_response: bytes = self.sock_data.recv(1024)
                # for testing, save the raw data to a file, append mode
                #with open('raw_data', 'ab') as f:
                #    f.write(raw_response)

                # next two bytes are the length of the frame, which we can trim, because
                # we can just read until we get the :END: footer
                raw_response = raw_response[2:]
                # on the first frame of a series of frames, we will get FECFEC at the beginning
                # of the data packet that ardopcf sends us. I think this is a bug.
                if raw_response.startswith(b'FECFEC'):
                    raw_response = raw_response[6:]
                # every other subsequent data packet will just have a single FEC prefixing it.
                elif raw_response.startswith(b'FEC'):
                    raw_response = raw_response[3:]
                elif raw_response.startswith(b'ERR'):
                    print("TNC sent error, ignoring.")
                    continue

                this_frame_data = raw_response
                
                # reset the timer if we got data
                start_time = time.time()
                # unfortunately, we really do need a footer.
                all_frame_data += this_frame_data
                if this_frame_data.endswith(b':END:'):
                    break

        return(all_frame_data)

    def abort(self):
        # abort actually sucks and doesn't work immediately
        # it's better to clear the buffer with PURGEBUFFER,
        # this makes the TNC stop transmitting, much better than ABORT
        self.cmd_response(command="ABORT", wait=False)

    def cmd_response(self, command=None, wait=False) -> str:
        if not self.is_ready():
            return(None)
        # if we run without a command, return immediately
        # if we run with a command, block until we get a response
        while True:
            timeout = 0
            if command:
                self.__send_cmd(command)
            if wait:
                timeout = None
            else:
                return(None)
            try:
                if self.sock_cmd in select.select([self.sock_cmd], [], [], timeout)[0]:
                    response = self.sock_cmd.recv(1024).decode() # all responses from the TNC are ASCII
                    return(response)
            except OSError as e:
                return(None)
    
    def listen_for_command_responses(self):
        # this is our main event loop for handling command responses from the TNC
        while not self.stop_event.is_set():
            if not self.is_ready():
                # try to reconnect to the TNC
                self.connect_to_ardopcf()
            response = self.cmd_response(wait=True)
            self.command_response_history.append(response)

            try:
                for entry in self.command_response_history:
                    # Everything the first things in this group are very time sensitive
                    if ('PTT TRUE' in entry) or ('T T' in entry):
                        self.state['ptt'] = True
                        self.host_interface.plugMgr.on_key_transmitter()
                    elif ('PTT FALSE' in entry) or ('T F' in entry):
                        self.state['ptt'] = False
                        self.host_interface.plugMgr.on_unkey_transmitter()
                    elif entry.startswith('BUFFER'):
                        self.state['buffer'] = entry.split()[1]
                    elif entry.startswith('STATE'):
                        self.state['state'] = entry.split()[1]
                    elif entry.startswith('FECSEND'):
                        pass
                    elif entry.startswith('MYCALL'):
                        self.state['mycall'] = entry.split()[2]
                    elif entry.startswith('GRIDSQUARE'):
                        self.state['gridsquare'] = entry.split()[2]
                    elif entry.startswith('FECMODE'):
                        self.state['fec_mode'] = entry.split()[2]
                    elif entry.startswith('FECREPEATS'):
                        self.state['fec_repeats'] = entry.split()[2]
                    elif entry.startswith('PROTOCOLMODE'):
                        self.state['protocol_mode'] = entry.split()[2]
                    else:
                        #print(f"Unhandled command response: {entry}")
                        pass
                    self.command_response_history.remove(entry)
                    # plugins might really interfere with this thread, it may be better
                    # to spawn a thread when this is called. Will test and change as needed.
                    self.host_interface.plugMgr.on_command_received(entry)
            except TypeError:
                # this is a catch for the case where the command_response_history is None
                # usually at program termination or on timeout
                pass

    def on_shutdown(self):
        self.stop_event.set()
        # this is a hack to get the command_response thread to exit
        # (it's blocking on a recv call until it gets a response from the TNC)
        self.cmd_response(command='STATE', wait=False)
        self.command_listen.join()
        self.sock_cmd.close()
        self.sock_data.close()
        sys.exit()
