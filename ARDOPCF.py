import socket
import select
import time
import threading
import sys


class ARDOPCF:
    def __init__(self, host_interface):
        self.stop_event = threading.Event()
        self.command_response_history = []
        self.host_interface = host_interface

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
            print("If you are using VOX (you SHOULD use CAT), you can type 'y' and press enter to ignore this error.")
            choice = input("Press enter to continue.")
            if choice != 'y':
                print("Exiting.")
                exit(1)
            self.sock_rigctld = None

        # FIXME: this is redudant with self.state
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
        self.command_listen = threading.Thread(target=self.listen_for_command_responses)
        self.command_listen.start()

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

    def __send_cmd(self, string):
        # Append the Carriage Return byte to the string
        string += '\r'
        self.sock_cmd.sendall(string.encode())


    def key_transmitter(self):
        if self.sock_rigctld:
            self.sock_rigctld.sendall(b'T 1\n')
            self.host_interface.plugins.on_key_transmitter()
        else:
            print("Cannot key transmitter, rigctld not connected")
    
    def unkey_transmitter(self):
        if self.sock_rigctld:
            self.sock_rigctld.sendall(b'T 0\n')
            self.host_interface.plugins.on_unkey_transmitter()
        else:
            print("Cannot unkey transmitter, rigctld not connected")
    
    def send_text_to_buffer(self, message : str):
        # this application only uses FEC mode (for now)
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

    def append_bytes_to_buffer(self, data : bytes):
        # this application only uses FEC mode
        # data format is <2 bytes for length><FEQ or ARQ><data>
        # data should already come here with the protocol header
        data = b'FEC' + data
        data_length = len(data).to_bytes(2, 'big')
        data = data_length + data
        self.sock_data.sendall(data)

    def transmit_buffer(self):
        # twice! because the TNC is a little finicky on first transmit
        self.cmd_response(command='FECSEND TRUE', wait=False)
        self.cmd_response(command='FECSEND TRUE', wait=False)
        self.host_interface.entry['state'] = 'normal'

    def clear_buffer(self):
        self.cmd_response(command='PURGEBUFFER', wait=False)
        self.host_interface.entry['state'] = 'normal'

    def recieve_from_data_buffer(self) -> bytes:
        # The TNC decodes audio, if there is a valid packet,
        # it puts into the data buffer.
        # Duplicate frames will not be passed to the host.
        try:
            if self.sock_data in select.select([self.sock_data], [], [], 0)[0]:
                raw_response: bytes = self.sock_data.recv(1024)
                # first two bytes are the length of the message
                message_length = int.from_bytes(raw_response[:2], 'big')
                # check if the message length is the actual length of the message
                if message_length != len(raw_response[2:]):
                    print("WARNING: ARDOP length does not match actual message length.")
                    print(f"ARDOP length: {message_length}, actual length: {len(raw_response[2:])}")
                raw_response = raw_response[2:]
                # next six bytes are "FECFEC", which we can trim
                raw_response = raw_response[6:]
                return(raw_response)
        except OSError as e:
            return(None)
        
    def cmd_response(self, command=None, wait=False) -> str:
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
        # this is our main loop for handling responses from the TNC
        while not self.stop_event.is_set():
            response = self.cmd_response(wait=True)
            self.command_response_history.append(response)

            try:
                for entry in self.command_response_history:
                    #might be a problem if a plugin starts blocking the main thread
                    #self.host_interface.plugins.on_command_received(entry)
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
                        #print(f"Unhandled command response: {entry}")
                        self.command_response_history.remove(entry)
            except TypeError:
                # this is a catch for the case where the command_response_history is None
                # usually at program termination
                pass

    def close_all(self):
        print("Halting transmission, closing all sockets, and exiting")
        self.unkey_transmitter()
        self.stop_event.set()
        # this is a hack to get the command_response thread to exit
        # (it's blocking on a recv call until it gets a response from the TNC)
        self.cmd_response(command='STATE', wait=False)
        self.command_listen.join()
        self.sock_cmd.close()
        self.sock_data.close()
        if self.sock_rigctld:
            self.sock_rigctld.close()
        
        sys.exit()
