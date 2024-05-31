import socket
import time
import threading
import tkinter as tk
import json
from hamChatPlugin import hamChatPlugin

"""
Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

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
            'version': '0.1',
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
        self.record_command_response = False

        self.command_listen = threading.Thread(target=self.listen_for_command_responses)
        self.command_listen.start()

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
            self.ready.set("Ready")
            self.init_tnc()
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
            

    def init_tnc(self):
        print("ARDOP Initializing TNC")
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
        print("ARDOP TNC Initialized")

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

        # command window button
        command_button = tk.Button(buttonframe, text="Command Window", command=self.show_command_window)
        command_button.pack(side=tk.LEFT)

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

    def append_bytes_to_buffer(self, data : bytes, mode: str = 'FEC'):
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
        
        modebytes = mode.encode()
        # if the data is too long, we can't send it without splitting it up
        # 1000 seems comfortable.
        for i in range(0, len(data), 1000):
            data_chunk = data[i:i+1000]
            # every chunk of data needs to be prefixed with the FEC prefix else the TNC will ignore it
            # this modem uses FEC mode by default for p2p chat
            # data format is <2 bytes for length><FEQ or ARQ><data>
            # data should already come here with the hamChat standard header
            data_chunk = modebytes + data_chunk
            data_length = len(data_chunk).to_bytes(2, 'big')
            data_chunk = data_length + data_chunk
            self.sock_data.sendall(data_chunk)

        # hopefully the TNC will have processed the data by now :^)
        time.sleep(0.2)
        if self.host_interface.debug.get():
            print(f"ARDOP Buffer Ready: {self.state.get('buffer')} bytes.")

    def on_transmit_buffer(self):
        # twice! because the TNC can be a little finicky on first transmit
        # also, sometimes the command recieve buffer will 'double up' on itself.
        self.cmd_response(command='FECSEND TRUE', wait=False)
        self.cmd_response(command='FECSEND TRUE', wait=False)

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

    # TODO: This, unfortunately, only handles FEC mode, and not ARQ mode.
    # It would make sense to implement ARQ mode so it would be possible to send CONREQ2000M frames
    def on_get_data(self) -> bytes:
        # This is blocking, and should run in its own thread
        # This will return ONE set of frames from the TNC, marked by the :END: footer
        # or until we see another FECFEC prefix, which means we have another data packet,
        # Ardop MAY CHANGE how it sends this. It's rather.... undefined.

        # the smallest data frame 4FSK.200.50S will encode just 16 data bytes
        # chances are that we will not receive a full frame in one go unless 
        # we are using a high data rate

        # no matter what frame we recieved, or the order we got the frame
        # we will always get the following bytes from the beginning of the data socket:
        # 2 bytes for the length of the frame
        # 6 bytes for the FECFEC prefix if the first frame of a series of frames (a bug?)
        # 3 bytes for the FEC prefix if not the first frame of a series of frames

        # we can detect if the message is over by checking if the end of the message is ':END:'
        # or if we simply stop getting data from the socket.

        # if ardop gets messages and nobody reads it, it will fill up ardop's data socket buffer

        # example Received data: b'K7OTR-1:chat:0.1:K7OTR:BEGIN:A much longer message, here it i\x00CFECs, here it is here it is, multiple farames fefjensfnrsribghilerb\x00\x0eFECrghbgr:END:'

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
                length = int.from_bytes(length, 'big')
                # get the rest of this data frame
                this_frame = self.sock_data.recv(length+3) # account for the FEC/ARQ/ERR msg prefix
                if self.host_interface.debug.get():
                    print(f"ARDOPCF: Incoming Frame: len:{length} data:{this_frame}")
                # remove the FECFEC and FEC prefix if it exists
                if this_frame[:6] == b'FECFEC':
                    this_frame = this_frame[6:]
                elif this_frame[:3] == b'FEC':
                    this_frame = this_frame[3:]
                elif this_frame[:3] == b'ARQ':
                    # discard ARQ frames, we don't use them yet
                    this_frame = b''
                    continue
                elif this_frame[:3] == b'ERR':
                    # discard error frames, we don't use them yet
                    this_frame = b''
                    continue
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
        # The main limitation is PTT control from ardop being very time sensitive.
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
    
    def listen_for_command_responses(self):
        # this is our main event loop for handling command responses from the TNC
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
            #if debug:
            #    print(f"ARDOP Response: {response}")

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
                        self.state['buffer'] = int(entry.split()[1])
                    elif entry.startswith('STATE'):
                        self.state['state'] = entry.split()[1]
                    elif entry.startswith('FECSEND'):
                        pass
                    elif entry.startswith('PROTOCOLMODE'):
                        self.state['protocol_mode'] = entry.split()[1]
                    else:
                        pass
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
