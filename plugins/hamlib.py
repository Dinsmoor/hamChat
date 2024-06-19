# inherits from hamChatPlugin
from hamChatPlugin import hamChatPlugin
import tkinter as tk
import socket
import time
# help us access the main hamChat class in our editor
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import HamChat
else:
    HamChat = None

"""
Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

class Hamlib(hamChatPlugin):
    def __init__(self, host_interface: HamChat):
        super().__init__(host_interface)

        self.info = f"""
        This plugin comminicates with the Hamlib library to control
        a radio via rigctld.
        On linux, you can start rigctld with the following command:
        rigctld -m 1234 -r /dev/ttyUSB0
        https://github.com/Dinsmoor/hamChat
        """
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Hamlib',
            'version': '0.1',
            'description': self.info,
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
        self.hamlib_status ={
            'status': 'Not connected',
            'frequency': '0Hz',
            'mode': 'MODE-PbHz',
            'ptt': 'False',
        }
        self.sock_rigctld = None
        self.rigctld_host = 'localhost'
        self.rigctld_port = '4532'
        self.status = tk.StringVar()
        self.configure_menu_error_message = "No error detected."
        self.rigctld_host_setting = tk.StringVar()
        self.rigctld_port_setting = tk.StringVar()
        self.rigctld_host_setting.set(self.rigctld_host)
        self.rigctld_port_setting.set(self.rigctld_port)
        self.hamlib_status_label = tk.Label()
        self.freq = tk.StringVar()
        self.mode = tk.StringVar()
        self.ptt = tk.StringVar()
        self.__open_rigctld_socket()
        

    def on_key_transmitter(self):
        if self.sock_rigctld is not None:
            try:
                self.sock_rigctld.sendall(b'T 1\n')
            except OSError:
                pass

    def on_unkey_transmitter(self):
        if self.sock_rigctld is not None:
            try:
                self.sock_rigctld.sendall(b'T 0\n')
            except OSError:
                pass

    def on_shutdown(self):
        if self.sock_rigctld is not None:
            self.on_unkey_transmitter()
            self.sock_rigctld.close()
    
    def create_plugin_frame(self, tkParent):
        self.hamlib_frame = tk.Frame(tkParent)
        statusframe = tk.Frame(self.hamlib_frame)
        statusframe.pack()
        hamlib_label = tk.Label(statusframe, text=self.definition['name'])
        hamlib_label.pack(side=tk.LEFT)
        self.hamlib_status_label = tk.Label(statusframe, textvariable=self.status)
        self.hamlib_status_label.pack(side=tk.RIGHT)
        if self.status.get() == "Connected":
            self.hamlib_status_label.config(fg='green')
        self.hamlib_freq_label = tk.Label(self.hamlib_frame, textvariable=self.freq)
        self.hamlib_freq_label.pack()
        self.hamlib_mode_label = tk.Label(self.hamlib_frame, textvariable=self.mode)
        self.hamlib_mode_label.pack()
        self.ptt_label = tk.Label(self.hamlib_frame, textvariable=self.ptt)
        self.ptt_label.pack()
        hamlib_button = tk.Button(self.hamlib_frame, text="Configure", command=self._open_hamlib_config_window)
        hamlib_button.pack(side=tk.BOTTOM)
        self.hamlib_frame.pack()

    def update_plugin_frame(self):
        if self.status.get() == "Connected":
            self.hamlib_status_label.config(fg='green')
            self.freq.set(f"{self.get_radio_frequency()}Hz")
            self.mode.set(f"{self.get_radio_mode()}")
            self.ptt.set(f"PTT: {self.get_ptt_status() == '1'}")
        else:
            self.hamlib_status_label.config(fg='red')
            self.status.set("Error")
            self.freq.set("")
            self.mode.set("")
            self.ptt.set("")

    
    def _open_hamlib_config_window(self):
        self.hamlib_config_window = tk.Toplevel()
        self.hamlib_config_window.title("Hamlib Configuration")
        top_frame = tk.Frame(self.hamlib_config_window)
        top_frame.pack(side=tk.TOP)
        tk.Label(top_frame, text="Configure rigctld connection").pack()
        
        self.rigctld_host_label = tk.Label(top_frame, text="Host:")
        self.rigctld_host_label.pack(side=tk.LEFT)
        self.rigctld_host_entry = tk.Entry(top_frame, textvariable=self.rigctld_host_setting)
        self.rigctld_host_entry.pack(side=tk.LEFT)
        self.rigctld_port_label = tk.Label(top_frame, text="Port:")
        self.rigctld_port_label.pack(side=tk.LEFT)
        self.rigctld_port_entry = tk.Entry(top_frame, textvariable=self.rigctld_port_setting)
        self.rigctld_port_entry.pack(side=tk.LEFT)
        self.hamlib_close_button = tk.Button(top_frame, text="Apply", command=self.__apply_hamlib_config)
        self.hamlib_close_button.pack(side=tk.LEFT)
        status_label = tk.Label(self.hamlib_config_window, text=self.configure_menu_error_message)
        status_label.pack()

    def __apply_hamlib_config(self):
        # check if they are different from what they were, if not, we don't need to do anything except close the window
        if self.rigctld_host == self.rigctld_host_entry.get() and self.rigctld_port == self.rigctld_port_entry.get():
            self.hamlib_config_window.destroy()
            return
        self.rigctld_host = self.rigctld_host_entry.get()
        self.rigctld_port = self.rigctld_port_entry.get()
        self.__open_rigctld_socket()
        self.hamlib_config_window.destroy()

    def __test_rigctld_connection(self):
        # sending 'f' to rigctld should return the frequency of the radio
        # example response: Frequency: 146450000

        self.sock_rigctld.sendall(b'f\n')
        response = self.read_rigctld_socket()
        return response
    
    def query_rigctld(self, command: str):
        # this should be continuously called in a separate thread
        time.sleep(0.5)
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(f'{command}\n'.encode())
            response = self.read_rigctld_socket()
            if not response:
                return
            self.parse_rigctld_response(response)

    def get_radio_frequency(self):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(b'f\n')
            response = self.read_rigctld_socket()
            # check if the response is a 9 digit number
            if not response.isdigit() or len(response) != 9:
                return
            # place dots in the frequency for readability
            response = response[:-6] + '.' + response[-6:-3] + '.' + response[-3:]
            return response
    
    def set_radio_frequency(self, frequency: int):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(f'F {frequency}\n'.encode())

    def get_radio_mode(self):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(b'm\n')
            mode = self.read_rigctld_socket()
            # check to see if the mode is a 3-6 character text string (no numbers)
            if not mode:
                return
            if not mode.isalpha():
                return
            passband = self.read_rigctld_socket()
            # check to see if the passband is a number longer than 1
            if not passband.isdigit() or len(passband) == 1:
                return
            
            return f"{mode}-{passband}Hz"
    
    def set_radio_mode(self, mode: str):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(f'M {mode}\n'.encode())

    def get_ptt_status(self):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(b't\n')
            status = self.read_rigctld_socket()
            if not status:
                return
            if len(status) == 1:
                return status


    def read_rigctld_socket(self):
        message = b''
        while True:
            try:
                message += self.sock_rigctld.recv(1)
                if message[-1:] == b'\n':
                    return message.decode().strip()
            except BlockingIOError:
                return False

    def IPC(self, target_plugin: str, from_plugin: str, command: str, data: bytes = None) -> dict:
        if not target_plugin == self.definition['name']:
            pass
        if command == "get_radio_frequency":
            return {"radio_frequency": self.get_radio_frequency()}
        elif command == "set_radio_frequency":
            self.set_radio_frequency(str(data))
            return {"radio_frequency": self.get_radio_frequency()}
        elif command == "get_radio_mode":
            return {"radio_mode": self.get_radio_mode()}
        elif command == "set_radio_mode":
            self.set_radio_mode(data.decode())
            return {"radio_mode": self.get_radio_mode()}
        elif command == "key_transmitter":
            self.on_key_transmitter()
            return {"status": "Transmitter keyed."}
        elif command == "unkey_transmitter":
            self.on_unkey_transmitter()
            return {"status": "Transmitter unkeyed."}
        elif command == "shutdown":
            self.on_shutdown()
            return {"status": "Plugin shut down."}
        elif command == "get_plugin_info":
            return self.definition
        elif command == "get_plugin_status":
            return {"status": self.status.get()}
        else:
            return {"error": "Command not recognized."}
    
    def parse_rigctld_response(self, response: str):
        # check if the response is a 9 digit number
        if response.isdigit() or len(response) != 9:
            # assume is a frequency
            response = response[:-6] + '.' + response[-6:-3] + '.' + response[-3:]
            self.hamlib_status['frequency'] = response
        if not response:
            return
        # check to see if the mode is a 3-6 character text string (no numbers)
        if response.isalpha():
            self.hamlib_status['mode'] = response
        # check to see if the passband is a number longer than 1
        if response.isdigit() and len(response) > 1:
            self.hamlib_status['mode'] += f"-{response}Hz"
        # check to see if the response is a 1 or 0
        if response == '1' or response == '0':
            self.hamlib_status['ptt'] = response
            
        

    def __open_rigctld_socket(self):
        try:
            if self.sock_rigctld is not None:
                self.sock_rigctld.close()
            self.sock_rigctld = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_rigctld.connect((self.rigctld_host, int(self.rigctld_port)))
            self.sock_rigctld.setblocking(False)
            self.__test_rigctld_connection() # we expect to throw an exception if we can't connect
            self.status.set("Connected")
            # make it green
            self.hamlib_status_label.config(fg='green')
            self.configure_menu_error_message = "No error detected."
        except BlockingIOError:
            pass
        except Exception as e:
            self.status.set("Error")
            # make it red
            self.hamlib_status_label.config(fg='red')
            error_type = type(e).__name__ 
            if error_type == "gaierror":
                error_type = "an incorrect hostname or IP address"
            self.configure_menu_error_message = f"Could not connect to rigctld due to {error_type}.\nPlease configure the plugin."