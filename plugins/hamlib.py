# inherits from hamChatPlugin
from hamChatPlugin import hamChatPlugin
import tkinter as tk
import socket

class Hamlib(hamChatPlugin):
    def __init__(self, host_interface: object):
        super().__init__(host_interface)

        self.info = f"""
        This plugin comminicates with the Hamlib library to control radios, via rigctld.
        On linux, you can start rigctld with the following command:
        rigctld -m 1234 -r /dev/ttyUSB0
        Right now, this plugin only supports a single radio.
        If you wanted multiple radios, you would need multiple copies of this plugin, but right
        now there is no way to specify which radio you are talking to. Might patch that in later.
        https://github.com/Dinsmoor/hamChat
        """
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Hamlib',
            'version': '0.1',
            'description': self.info,
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
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
        hamlib_button = tk.Button(self.hamlib_frame, text="Configure", command=self._open_hamlib_config_window)
        hamlib_button.pack(side=tk.BOTTOM)
        self.hamlib_frame.pack()

    
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
        response = self.sock_rigctld.recv(1024).decode().strip()
        # place dots in the frequency for readability
        response = response[:-6] + '.' + response[-6:-3] + '.' + response[-3:]
        return response
    
    def get_radio_frequency(self):
        return self.__test_rigctld_connection()
    
    def set_radio_frequency(self, frequency: int):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(f'F {frequency}\n'.encode())
            return self.__test_rigctld_connection()
        else:
            self.host_interface.print_to_chatwindow("Not connected to rigctld." )

    def get_radio_mode(self):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(b'm\n')
            return self.sock_rigctld.recv(1024).decode().strip()
        else:
            self.host_interface.print_to_chatwindow("Not connected to rigctld." )
    
    def set_radio_mode(self, mode: str):
        if self.sock_rigctld is not None:
            self.sock_rigctld.sendall(f'M {mode}\n'.encode())
            return self.sock_rigctld.recv(1024).decode().strip()
        else:
            self.host_interface.print_to_chatwindow("Not connected to rigctld." )

    def __open_rigctld_socket(self):
        try:
            if self.sock_rigctld is not None:
                self.sock_rigctld.close()
            self.sock_rigctld = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_rigctld.connect((self.rigctld_host, int(self.rigctld_port)))
            self.__test_rigctld_connection()
            self.status.set("Connected")
            # make it green
            self.hamlib_status_label.config(fg='green')
            self.configure_menu_error_message = "No error detected."
        except Exception as e:
            self.status.set("Error")
            # make it red
            self.hamlib_status_label.config(fg='red')
            error_type = type(e).__name__ 
            if error_type == "gaierror":
                error_type = "an incorrect hostname or IP address"
            self.configure_menu_error_message = f"Could not connect to rigctld due to {error_type}.\nPlease configure the plugin."