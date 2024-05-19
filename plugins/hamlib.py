# inherits from hamChatPlugin
from hamChatPlugin import hamChatPlugin
import tkinter as tk
import socket
import select

class Hamlib(hamChatPlugin):
    def __init__(self, host_interface: object):
        super().__init__(host_interface)

        self.info = f"""
        This plugin comminicates with the Hamlib library to control radios, via rigctld.
        On linux, you can start rigctld with the following command:
        rigctld -m 1234 -r /dev/ttyUSB0
        """
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Hamlib',
            'version': '0.1',
            'description': self.info,
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
        self.sock_rigctld = None
        self.rigctld_host = tk.StringVar()
        self.rigctld_port = tk.StringVar()
        self.rigctld_host.set('localhost')
        self.rigctld_port.set('4532')
        # we will connect to the port when the ui is created
        

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
            self.host_interface.write_message("Hamlib plugin shutting down.")
    
    def on_ui_create_widgets(self):
        self.hamlib_frame = tk.Frame(self.host_interface.plugins_frame)
        self.hamlib_label = tk.Label(self.hamlib_frame, text=self.definition['name'])
        self.hamlib_label.pack(side=tk.TOP)
        self.hamlib_button = tk.Button(self.hamlib_frame, text="Configure", command=self._open_hamlib_config_window)
        self.hamlib_button.pack(side=tk.LEFT)
        self.hamlib_frame.pack()
        self.__open_rigctld_socket()

    
    def _open_hamlib_config_window(self):
        self.hamlib_config_window = tk.Toplevel()
        self.hamlib_config_window.title("Hamlib Configuration")
        tk.Label(self.hamlib_config_window, text="Configure rigctld connection").pack()
        self.rigctld_host_label = tk.Label(self.hamlib_config_window, text="Host:")
        self.rigctld_host_label.pack(side=tk.LEFT)
        self.rigctld_host_entry = tk.Entry(self.hamlib_config_window, textvariable=self.rigctld_host)
        self.rigctld_host_entry.pack(side=tk.LEFT)
        self.rigctld_port_label = tk.Label(self.hamlib_config_window, text="Port:")
        self.rigctld_port_label.pack(side=tk.LEFT)
        self.rigctld_port_entry = tk.Entry(self.hamlib_config_window, textvariable=self.rigctld_port)
        self.rigctld_port_entry.pack(side=tk.LEFT)
        self.hamlib_close_button = tk.Button(self.hamlib_config_window, text="Apply", command=self.__apply_hamlib_config)
        self.hamlib_close_button.pack(side=tk.LEFT)

    def __apply_hamlib_config(self):
        self.__open_rigctld_socket()
        self.hamlib_config_window.destroy()

    def __test_rigctld_connection(self):
        # sending 'f' to rigctld should return the frequency of the radio
        # example response: Frequency: 146450000

        self.sock_rigctld.sendall(b'f\n')
        response = self.sock_rigctld.recv(1024).decode().strip()
        # place dots in the frequency for readability
        response = response[:-6] + '.' + response[-6:-3] + '.' + response[-3:]
        return response

    def __open_rigctld_socket(self):
        try:
            if self.sock_rigctld is not None:
                self.sock_rigctld.close()
            self.sock_rigctld = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_rigctld.connect((self.rigctld_host.get(), int(self.rigctld_port.get())))
            frequency = self.__test_rigctld_connection()
            self.host_interface.write_message(f"Connected to rigctld at {self.rigctld_host.get()}:{self.rigctld_port.get()}, radio frequency is {frequency} Hz.")
        except Exception as e:
            error_type = type(e).__name__ 
            if error_type == "gaierror":
                error_type = "an incorrect hostname or IP address"
            self.host_interface.write_message(f"Could not connect to rigctld due to {error_type}. Please configure the plugin.")