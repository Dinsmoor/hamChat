import tkinter as tk
import threading
import time
import json
from ARDOPCF import ARDOPCF
from PluginManager import PluginManager

info = """
This application is a simple chat application that interfaces
with the ARDOPC client the ARDOPC client is a TNC that uses the
ARDOP protocol and is used for digital communications over any
audio band, but is most commonly used in amateur radio for HF
and VHF communications.
It uses tkinter for the GUI and the ARDOPCF client for the TNC,
and most features are extensible through the use of plugins.

This application is a work in progress and is not yet complete.
"""


class ARDOPCFGUI(tk.Tk):
    def __init__(self):
        """
        This is the main application window for the ARDOP Chat application.
        all incoming and outgoing messages will be prefixed with a header.
        a typical message will look like this:
        N0CALL:chat:0.1:BEGIN:Hello, world!
        Index 0: Callsign
        Index 1: Protocol Identifier
        Index 2: Protocol Version
        Index -1: END
        All other indexes until ":BEGIN:" are reserved for a plugin to use as it sees fit.
        """
        tk.Tk.__init__(self)
        self.version = '0.1'
        self.title("ARDOPCF Chat")
        self.resizable(True, True)
        self.geometry("500x768")
        self.settings = {
            'callsign': 'N0CALL',
            'gridsquare': 'AA00AA',
            'fec_mode': '4FSK.200.50S',
            'fec_repeats': 1,
            'use_message_history': 1
        }

        self.die = threading.Event()
        # kill yourself.
        
        # hopefully not a race condition here :cringe:
        self.plugins = PluginManager(host_interface=self, plugin_folder='ARDOPCF_Plugins')
        self.ardop = ARDOPCF(host_interface=self)
        try:
            self._load_settings_from_file()
            self.ardop.init_tnc()
        except FileNotFoundError:
            pass
        self.create_widgets()
        
        # make sure the sockets are closed when the application is closed
        self.protocol("WM_DELETE_WINDOW", self.ardop.close_all)
        self.message_history = []
        
        # these two need to be on their own threads
        self.data_listener = threading.Thread(target=self.listen_for_data)
        self.data_listener.start()
        self.ui_updater = threading.Thread(target=self.update_ui_ardop_state)
        self.ui_updater.start()

    def _save_settings_to_file(self):
        with open('chat_settings.json', 'w') as f:
            f.write(json.dumps(self.settings))

    def _load_settings_from_file(self):
        with open('chat_settings.json', 'r') as f:
            self.settings = json.loads(f.read())
        self.apply_settings()

    def save_message_history(self):
        with open('message_history.txt', 'w') as f:
            for message in self.message_history:
                f.write(message+'\n')
    
    def _load_message_history(self):
        with open('message_history.txt', 'r') as f:
            self.message_history = f.readlines()

    def create_widgets(self):
        self.message_box = tk.Text(self, width=60, height=20)
        self.scrollbar = tk.Scrollbar(self, command=self.message_box.yview)
        self.message_box.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.message_box.config(wrap=tk.WORD)
        
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
        self.entry_label = tk.Label(self, text="Enter Message:")
        self.entry_label.pack()

        self.entry = tk.Entry(self, width=60)
        self.entry.bind("<Return>", lambda event: self.send_chat_message())
        self.entry.pack()


        self.native_button_frame = tk.Frame(self)
        self.send_button = tk.Button(self.native_button_frame, text="Send", command=self.send_chat_message)
        # disable the send button until the user enters a message
        self.send_button['state'] = 'disabled'
        # enable the chat send button when the user types something
        self.entry.bind("<Key>", lambda event: self.send_button.config(state='normal'))
        self.send_button.pack(side=tk.LEFT)

        self.clear_buffer_button = tk.Button(self.native_button_frame, text="Clear Buffer/Stop", command=self.ardop.clear_buffer)
        self.clear_buffer_button.pack(side=tk.LEFT)

        self.settings_button = tk.Button(self.native_button_frame, text="Settings", command=self.create_settings_menu)
        self.settings_button.pack(side=tk.LEFT)

        self.info_button = tk.Button(self.native_button_frame, text="About", command=self.display_info_box)
        self.info_button.pack(side=tk.LEFT)
        self.native_button_frame.pack()

        self.plugins_frame = tk.Frame(self)
        self.plugins.on_ui_create_widgets()
        self.plugins_frame.pack()

        self.status_bar_frame = tk.Frame(self)
        self.ardop_state_label = tk.Label(self.status_bar_frame, text="TNC State:")
        self.ardop_state_label.grid(row=0, column=0)
        self.ardop_state_string = tk.StringVar()
        self.ardop_state = tk.Label(self.status_bar_frame, textvariable=self.ardop_state_string)
        self.ardop_state.grid(row=0, column=1)

        self.ardop_buffer_string = tk.StringVar()
        self.ardop_buffer_label = tk.Label(self.status_bar_frame, text="DATA Buffer:")
        self.ardop_buffer_label.grid(row=1, column=0)
        self.ardop_buffer = tk.Label(self.status_bar_frame, textvariable=self.ardop_buffer_string)
        self.ardop_buffer.grid(row=1, column=1)
        self.status_bar_frame.pack(side=tk.BOTTOM)

    def write_message(self, message: str):
        self.message_box.config(state=tk.NORMAL)
        self.message_box.insert(tk.END, message+'\n')
        if self.settings['use_message_history']:
            self.message_history.append(message)
            if len(self.message_history) > 500:
                self.message_history.pop(0)
        self.message_box.config(state=tk.DISABLED)
    
    def display_info_box(self):
        info_box = tk.Toplevel(self)
        info_box.title("About ARDOP Chat")
        info_box.geometry("500x300")
        info_label = tk.Label(info_box, text=info)
        info_label.pack()
        close_button = tk.Button(info_box, text="Close", command=info_box.destroy)
        close_button.pack()
    
    def estimate_minutes_to_send(self):
        return(int(self.ardop.state.get("buffer")) / self.ardop.rate_table[self.settings['fec_mode']])

    def display_warning_box(self, message):
        warning_box = tk.Toplevel(self)
        warning_box.title("Warning")
        warning_box.geometry("300x300")
        warning_label = tk.Label(warning_box, text=message)
        warning_label.pack()
        close_button = tk.Button(warning_box, text="Close", command=warning_box.destroy)
        close_button.pack()

    def send_chat_message(self):
        message = self.entry.get()
        message = f"{self.settings['callsign']}:chat:{self.version}:BEGIN:{message}:END:"
        self.ardop.append_bytes_to_buffer(message.encode())
        self.ardop.transmit_buffer()

        self.entry.delete(0, tk.END)
        self.write_message(f"{message.split(':')[0]}: {message.split(':')[4]}")
        self.send_button['state'] = 'disabled'
        self.save_message_history()
    
    def listen_for_data(self):
        while not self.die.is_set():
            print("Listening for data...")
            # This will block until data is received.
            # Bytes returned have the format:
            data: bytes = self.ardop.recieve_from_data_buffer()

            if b":BEGIN:" in data:
                print(f"Received data: {data}")
                header = data.split(b':BEGIN:')[0]
                # get everyting between :BEGIN: and :END:
                payload = data.split(b':BEGIN:')[1].split(b':END:')[0]

                # we handle chat in the main application, not in a plugin because the chat is integral to the program
                if b":chat:" in header:
                    message = header.split(b":")[0] +b": " + payload
                    self.write_message(message.decode())
                
                for plugin in self.plugins.plugins:
                    for handler in plugin.definition['handlers']:
                        if handler in header.split(b':')[1].decode():
                            remote_plugin_version = header.split(b':')[2].decode()
                            if plugin.definition['version'] != remote_plugin_version:
                                self.display_warning_box(f'''Local plugin {plugin.__class__.__name__} has version mismatch
                                                        with remote plugin {remote_plugin_version}.\n 
                                                        Data may not be handled correctly.''')
                            # we have a plugin that can handle this data, it will do
                            # whatever in this interface it needs to do without further handling here.
                            plugin.on_data_received({'header': header, 'payload': payload})
                
                print(f"Received data: {data}")
                self.save_message_history()
    
    def update_ui_ardop_state(self):
        while not self.die.is_set():
            self.ardop.cmd_response(command='STATE', wait=False)
            self.ardop.cmd_response(command='BUFFER', wait=False)
            self.ardop_state_string.set(self.ardop.state['state'])
            time_to_send = self.estimate_minutes_to_send()
            time_to_send = int(time_to_send)
            self.ardop_buffer_string.set(f"{self.ardop.state['buffer']} : {time_to_send}m @ {self.settings['fec_mode']}")
            self.plugins.on_ui_ardop_state_update()
            time.sleep(0.5) # update every half second
    
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
        self.save_message_history_var = tk.IntVar()
        self.save_message_history_var.set(1)
        self.save_message_history_checkbutton = tk.Checkbutton(self.settings_menu, text="Save Message History", variable=self.save_message_history_var)
        self.save_message_history_checkbutton.pack()

        # allow plugins to add additional settings
        self.plugins.on_ui_create_settings_menu()

        self.save_button = tk.Button(self.settings_menu, text="Save", command=self.save_settings)
        self.save_button.pack()
        self.cancel_button = tk.Button(self.settings_menu, text="Cancel", command=self.settings_menu.destroy)
        self.cancel_button.pack()

    def save_settings(self):
        self.settings['callsign'] = self.callsign_entry.get()
        self.settings['gridsquare'] = self.gridsquare_entry.get()
        self.settings['fec_mode'] = self.fec_mode_var.get()
        self.settings['fec_repeats'] = self.fec_repeats_entry.get()
        self.settings['use_message_history'] = self.save_message_history_var.get()
        self.apply_settings()
        print(self.settings)
        self._save_settings_to_file()
        self.write_message(f"Client Settings Updated")
        self.settings_menu.destroy()
    
    def apply_settings(self):
        self.ardop.callsign = self.settings['callsign']
        self.ardop.gridsquare = self.settings['gridsquare']
        self.ardop.fec_mode = self.settings['fec_mode']
        self.ardop.fec_repeats = self.settings['fec_repeats']
        self.ardop.cmd_response(command=f'MYCALL {self.settings["callsign"]}', wait=False)
        self.ardop.cmd_response(command=f'GRIDSQUARE {self.settings["gridsquare"]}', wait=False)
        self.ardop.cmd_response(command=f'FECMODE {self.settings["fec_mode"]}', wait=False)
        self.ardop.cmd_response(command=f'FECREPEATS {self.settings["fec_repeats"]}', wait=False)
        self.plugins.on_ui_save_settings()

if __name__ == '__main__':
    ardop_chat_ui = ARDOPCFGUI()
    ardop_chat_ui.mainloop()