import socket
import select
import time
import threading
import sys


class ARDOPCF:
    def __init__(self, host_interface):
        self.stop_event = threading.Event()
        self.data_transfer_complete = threading.Event()
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

        self.rate_table = {
            # everything that's 10 is unknown, it's not in the appendix C of the ARDOP spec that I saw.
            '4FSK.200.50S': 310,
            '4PSK.200.100S': 436,
            '4PSK.200.100': 756,
            '8PSK.200.100': 1286,
            '16QAM.200.100': 1512,

            '4FSK.500.100S': 10, 
            '4FSK.500.100': 10,
            '4PSK.500.100': 1509,
            '8PSK.500.100': 2566,
            '16QAM.500.100': 3024,

            '4PSK.1000.100': 3018,
            '8PSK.1000.100': 5133,
            '16QAM.1000.100': 6036,

            '4PSK.2000.100': 6144,
            '8PSK.2000.100': 10386,
            '16QAM.2000.100': 12072,
            '4FSK.2000.600': 10,
            '4FSK.2000.600S': 10
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

        # if the data is too long, we can't send it without splitting it up
        # 1000 seems comfortable.

        for i in range(0, len(data), 1000):
            data_chunk = data[i:i+1000]
            # every chunk of data needs to be prefixed with the FEC prefix else the TNC will ignore it
            data_chunk = b'FEC' + data_chunk
            data_length = len(data_chunk).to_bytes(2, 'big')
            data_chunk = data_length + data_chunk
            self.sock_data.sendall(data_chunk)

    def transmit_buffer(self):
        # twice! because the TNC is a little finicky on first transmit
        self.cmd_response(command='FECSEND TRUE', wait=False)
        self.cmd_response(command='FECSEND TRUE', wait=False)
        self.host_interface.entry['state'] = 'normal'

    def clear_buffer(self):
        self.cmd_response(command='PURGEBUFFER', wait=False)
        self.host_interface.entry['state'] = 'normal'

    def recieve_from_data_buffer(self) -> bytes:
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
        # every series of frames, initially just wait forever
        listen_time = None
        start_time = time.time()

        while not self.stop_event.is_set():
            # no data for a while? give up
            if time.time() - start_time > timeout:
                break
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
                listen_time = 0.1

        return(all_frame_data)

    def abort(self):
        # abort actually sucks and doesn't work immediately
        # it's better to clear the buffer with PURGEBUFFER,
        # this makes the TNC stop transmitting immediately, much better than ABORT
        self.cmd_response(command="ABORT", wait=False)

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
        # this is our main event loop for handling command responses from the TNC
        while not self.stop_event.is_set():
            response = self.cmd_response(wait=True)
            self.command_response_history.append(response)

            try:
                for entry in self.command_response_history:
                    # might be a problem if a plugin starts blocking the main thread
                    # I am not touching it because it was a pain to get working.
                    # later, I'll stop removing the entry until the plugins get a copy of the command
                    # right now, its not implemented.
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
        self.host_interface.die.set()
        # this is a hack to get the command_response thread to exit
        # (it's blocking on a recv call until it gets a response from the TNC)
        self.cmd_response(command='STATE', wait=False)
        self.command_listen.join()
        self.sock_cmd.close()
        self.sock_data.close()
        if self.sock_rigctld:
            self.sock_rigctld.close()
        
        sys.exit()
