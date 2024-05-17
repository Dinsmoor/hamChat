import threading
import tkinter as tk
import json
from ARDOPCF import ARDOPCF
from PluginManager import PluginManager

info = """
This application is a simple chat application that interfaces with the ARDOPC client
the ARDOPC client is a TNC that uses the ARDOP protocol
and is used for digital communications over any audio band, but is most commonly used
in amateur radio for HF and VHF communications.
It uses tkinter for the GUI and the ARDOPCF client for the TNC, and most features are
extensible through the use of plugins.

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
        All other indexes until ":BEGIN:" are reserved for a plugin to use as it sees fit.
        """
        tk.Tk.__init__(self)
        self.version = '0.1'
        self.title("ARDOP Chat")
        self.resizable(True, True)
        self.geometry("500x600")
        self.settings = {
            'callsign': 'N0CALL',
            'gridsquare': 'AA00AA',
            'fec_mode': '4FSK.200.50S',
            'fec_repeats': 1,
            'use_message_history': 1
        }
        self.ardop = ARDOPCF(self)
        self.plugins = PluginManager(host_interface=self, plugin_folder='ARDOPCF_Plugins')
        try:
            self._load_settings_from_file()
            self.ardop.init_tnc()
        except FileNotFoundError:
            pass
        self.create_widgets()
        
        # make sure the sockets are closed when the application is closed
        self.protocol("WM_DELETE_WINDOW", self.ardop.close_all)
        self.message_history = []
        
        self.listen_for_data()
        self.update_ui_ardop_state()

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
        # Simple chat-related functions are integral to the program.
        # this progam should always retain chat functions.

        # this is the main chat window and will return the messages from the ARDOPC client
        # from the receive buffer. We do not enter commands here, only messages.
        self.message_box = tk.Text(self, width=60, height=20)
        # make the message box scrollable
        self.scrollbar = tk.Scrollbar(self, command=self.message_box.yview)
        self.message_box.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # make the message box word wrap
        self.message_box.config(wrap=tk.WORD)
        
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
        self.entry.bind("<Return>", lambda event: self.send_chat_message())
        self.entry.pack()
        self.send_button = tk.Button(self, text="Send", command=self.send_chat_message)
        #disable the send button until the user enters a message
        self.send_button['state'] = 'disabled'
        self.entry.bind("<Key>", lambda event: self.send_button.config(state='normal'))
        self.send_button.pack()

        self.plugins.on_ui_create_widgets()

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
        info_box.geometry("300x300")
        info_label = tk.Label(info_box, text=info)
        info_label.pack()
        close_button = tk.Button(info_box, text="Close", command=info_box.destroy)
        close_button.pack()
    
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
        message = f"{self.settings['callsign']}:chat:{self.version}:BEGIN:{message}"
        if self.ardop.append_bytes_to_buffer(message.encode()):
            transmit_thread = threading.Thread(target=self.ardop.transmit_buffer)
            transmit_thread.start()
        else:
            self.write_message("Could not send message, file too large or other error.")

        self.entry.delete(0, tk.END)
        self.write_message(message)
        self.send_button['state'] = 'disabled'
        self.save_message_history()
    
    def listen_for_data(self):
        data: bytes = self.ardop.recieve_from_data_buffer()
        
        if data:
            header = data.split(b':BEGIN:')[0]
            payload = data.split(b':BEGIN:')[1]

            # we handle chat in the main application, not in a plugin because the chat is integral to the program
            if b":chat:" in header:
                message: str = str(header.split(b":")[0]) + payload.decode()
                self.write_message(message)
            
            for plugin in self.plugins.plugins:
                for handler in plugin.definition['handlers']:
                    if handler in header.split(b':')[1].decode():
                        remote_plugin_version = header.split(b':')[2].decode()
                        if plugin.definition['version'] != remote_plugin_version:
                            self.display_warning_box(f"Local plugin {plugin.__class__.__name__} has version mismatch with remote plugin {remote_plugin_version}.\n/
                                                     Data may not be handled correctly.")
                        # we have a plugin that can handle this data, it will do
                        # whatever in this interface it needs to do without further handling here.
                        plugin.on_data_received({'header': header, 'payload': payload})
            
            print(f"Received data: {data}")
            
            self.save_message_history()
        self.after(1000, self.listen_for_data)
    
    def update_ui_ardop_state(self):
        self.ardop.cmd_response(command='STATE', wait=False)
        self.ardop.cmd_response(command='BUFFER', wait=False)
        self.ardop_state_string.set(self.ardop.state['state'])
        self.ardop_buffer_string.set(self.ardop.state['buffer'])
        self.plugins.on_ui_ardop_state_update()

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