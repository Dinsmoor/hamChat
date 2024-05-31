import tkinter as tk
from tkinter import ttk
import threading
import time
import json
from PluginManager import PluginManager
from hamChatPlugin import hamChatPlugin
import sys
import socket

info = """
This program is a desktop application that allows amatuer
radio operators to do almost whatever they want within the
context of text or binary data transfer, via a plugin system.

This application is a work in progress and is not yet complete.

Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""


class HamChat(tk.Tk):
    def __init__(self):
        """
        This is the main application window for the ARDOP Chat application.
        all incoming and outgoing messages will be prefixed with a flexible header.
        a typical chat message will look like this (SUBJECT TO CHANGE):
           0    1    2      3        4          5         6 (-1)
        N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
        Index 0: Sender Callsign 
        Index 1: Protocol Identifier
        Index 2: Protocol Version
        Index 3: Recipient Callsigns (optional, comma separated)
        Index 4: BEGIN Header
        Index 5: Payload (can be anything)
        Index -1: END Footer
        All other indexes until ":BEGIN:" are reserved for a plugin to use as it sees fit.
        """
        tk.Tk.__init__(self)
        self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.version = '0.1'
        our_hostname = socket.gethostname()
        self.title(f"hamChat@{our_hostname}")
        self.resizable(True, True)
        self.geometry("800x500")
        self.settings = {
            'callsign': 'N0CALL',
            'recipients': 'ALL',
            'gridsquare': 'AA00AA',
            'selected_transport': 'ARDOP',
            'use_message_history': 1
        }
        self._load_settings_from_file()
        self.message_history = []
        self.plugin_preload_messages = []

        self.die = threading.Event()
        self.ui_ready = threading.Event()
        self.transport_status_ready = threading.Event()
        self.transport_status_frame = tk.Frame(self)
        self.debug = tk.BooleanVar()
        self.debug.set(False)
        

        # there is a race condition between the plugins needing to access to the ui and the ui being created
        self.plugMgr = PluginManager(host_interface=self)
        self.plugMgr.load_plugins('plugins')
        self.transport = self.get_selected_transport()
        # avoid any issues with transports having a buffer that might interfere with messages
        self.plugMgr.on_clear_buffer()
        
        self.create_widgets()
        self.ui_ready.set()

        # list of last heard stations, a list of lists (may move to sqlite later)
        # [callsign, time, freq, mode, signal_strength, signal_quality] (callsign + time required, others if available)
        self.recently_heard_stations = []

        # everything below here shits themselves if a transport
        # has a time.sleep in a loop while waiting for anything.

        # these two need to be on their own threads
        self.data_listener = threading.Thread(target=self.listen_for_data)
        self.data_listener.start()
        self.transport_status_frame_thread = threading.Thread(target=self.update_transport_state_frame)
        self.transport_status_frame_thread.start()
        # this is very important for making sure self.transport is pointing to the correct plugin
        # will run in main thread, but will be updated by the transport_status_frame thread
        self.update_ui_transport_state()

    def log_recently_heard(self, callsign, time, freq=None, mode=None, signal_strength=None, signal_quality=None):
        self.recently_heard_stations.append([callsign, time, freq, mode, signal_strength, signal_quality])
        

    def get_selected_transport(self) -> hamChatPlugin:
        # this is set by the menu bar
        for plugin in self.plugMgr.plugins:
            if plugin.definition['transport'] == self.settings['selected_transport']:
                return plugin

    def _save_settings_to_file(self):
        with open('chat_settings.json', 'w') as f:
            f.write(json.dumps(self.settings))

    def _load_settings_from_file(self):
        try:
            with open('chat_settings.json', 'r') as f:
                self.settings.update(json.loads(f.read()))
        except FileNotFoundError:
            # if the file doesn't exist, we will just use the defaults
            pass

    def save_message_history(self):
        if not self.settings['use_message_history']:
            return
        with open('message_history.txt', 'w') as f:
            for message in self.message_history:
                f.write(message+'\n')
    
    def _load_message_history(self):
        with open('message_history.txt', 'r') as f:
            self.message_history = f.readlines()
        
    def _put_message_history_in_message_box(self):
        if self.settings['use_message_history']:
            self.message_box.config(state=tk.NORMAL)
            try:
                self._load_message_history()
                for message in self.message_history:
                    self.message_box.insert(tk.END, message)
            except FileNotFoundError:
                pass
            self.message_box.config(state=tk.DISABLED)

    def delete_message_history(self):
        self.message_box.config(state=tk.NORMAL)
        self.message_box.delete(1.0, tk.END)
        self.message_box.config(state=tk.DISABLED)
        self.message_history = []
        self.save_message_history()

    def create_recently_heard_treeview_window(self):
        recently_heard_window = tk.Toplevel(self)
        recently_heard_window.title("Recently Heard Stations")
        recently_heard_window.geometry("800x500")
        recently_heard_treeview = ttk.Treeview(recently_heard_window)
        recently_heard_treeview["columns"] = ("callsign", "time", "freq", "mode", "signal_strength", "signal_quality")
        recently_heard_treeview.column("#0", width=0, stretch=tk.NO)
        recently_heard_treeview.column("callsign", anchor=tk.W, width=100)
        recently_heard_treeview.column("time", anchor=tk.W, width=100)
        recently_heard_treeview.column("freq", anchor=tk.W, width=100)
        recently_heard_treeview.column("mode", anchor=tk.W, width=100)
        recently_heard_treeview.column("signal_strength", anchor=tk.W, width=100)
        recently_heard_treeview.column("signal_quality", anchor=tk.W, width=100)
        recently_heard_treeview.heading("#0", text="", anchor=tk.W)
        recently_heard_treeview.heading("callsign", text="Callsign", anchor=tk.W)
        recently_heard_treeview.heading("time", text="Time", anchor=tk.W)
        recently_heard_treeview.heading("freq", text="Frequency", anchor=tk.W)
        recently_heard_treeview.heading("mode", text="Mode", anchor=tk.W)
        recently_heard_treeview.heading("signal_strength", text="Signal Strength", anchor=tk.W)
        recently_heard_treeview.heading("signal_quality", text="Signal Quality", anchor=tk.W)
        for station in self.recently_heard_stations:
            recently_heard_treeview.insert("", tk.END, values=station)
        recently_heard_treeview.pack(fill=tk.BOTH, expand=True)

    def create_plugin_info_window(self, plugin):
        plugin_info_window = tk.Toplevel(self)
        plugin_info_window.title(f"{plugin.definition['name']} Info")
        plugin_info_window.geometry("500x300")
        plugin_textbox = tk.Text(plugin_info_window, width=60, height=20)
        plugin_textbox.config(wrap=tk.WORD, state=tk.NORMAL)
        plugin_textbox.pack()

        # iterate over every field in plugin.definition and display it
        # in a label
        for key, value in plugin.definition.items():
            # exclude empty values
            if not value:
                continue
            if key == 'depends_on':
                for value in value:
                    plugin_textbox.insert(tk.END, f"Depends on: {value['plugin']} version {value['version']}\n")
                continue
            key = key.capitalize()
            value = str(value)
            # remove multiple spaces and newlines
            value = ' '.join(value.split())
            plugin_textbox.insert(tk.END, f"{key}: {value}\n")
        plugin_textbox.config(state=tk.DISABLED)

        close_button = tk.Button(plugin_info_window, text="Close", command=plugin_info_window.destroy)
        close_button.pack()

    def create_menubar(self):
        self.menubar = tk.Menu(self)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Clear Message History", command=self.delete_message_history)
        self.filemenu.add_command(label="Recently Heard Stations", command=self.create_recently_heard_treeview_window)
        self.filemenu.add_command(label="Settings", command=self.create_settings_menu)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.shutdown)
        self.menubar.add_cascade(label="File", menu=self.filemenu)

        self.transportmenu = tk.Menu(self.menubar, tearoff=0)
        for plugin in self.plugMgr.plugins:
            if plugin.definition.get('transport'):
                self.transportmenu.add_command(label=plugin.definition['name'], command=lambda plugin=plugin: self.update_selected_transport(plugin.definition['transport']))       
        self.menubar.add_cascade(label="Transports", menu=self.transportmenu)

        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label="About hamChat", command=self.display_info_box)
        self.menubar.add_cascade(label="Help", menu=self.helpmenu)

        self.pluginsmenu = tk.Menu(self.menubar, tearoff=0)
        for plugin in self.plugMgr.plugins:
            self.pluginsmenu.add_command(label=plugin.definition['name'], command=lambda plugin=plugin: self.create_plugin_info_window(plugin))
        self.helpmenu.add_cascade(label="Plugins", menu=self.pluginsmenu)

        self.config(menu=self.menubar)

    def update_selected_transport(self, transport):
        self.settings['selected_transport'] = transport
        self.transport = self.get_selected_transport()

    def create_chat_frame(self):
        # the main frame for the chat window, will hold message box, scroll bar, and entry area
        self.chat_frame = tk.Frame(self.top_section, bd=2, relief=tk.SUNKEN)
        self.chat_frame.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        # this frame will hold the message/recipients entry and the send/clear buttons
        self.chat_user_entry_container = tk.Frame(self.chat_frame, bd=2, relief=tk.SUNKEN)
        self.chat_user_entry_container.pack(side=tk.TOP, fill=tk.X)

        # this frame holds the message entry and recipients entry (and their labels)
        self.chat_entry_area_frame = tk.Frame(self.chat_user_entry_container, bd=2, relief=tk.SUNKEN)
        self.chat_entry_area_frame.pack(side=tk.LEFT)

        # this frame holds the send and clear buttons, and should be right next to the chat entry area
        self.native_button_frame = tk.Frame(self.chat_user_entry_container, bd=2, relief=tk.SUNKEN)
        self.native_button_frame.pack(side=tk.RIGHT)

        self.message_box = tk.Text(self.chat_entry_area_frame, width=60, height=20)
        self.scrollbar = tk.Scrollbar(self.chat_user_entry_container, command=self.message_box.yview)
        self.message_box.config(wrap=tk.WORD, state=tk.DISABLED, yscrollcommand=self.scrollbar.set)
        self.message_box.see(tk.END)
        self.message_box.pack(fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._put_message_history_in_message_box()

        tk.Label(self.chat_entry_area_frame, text="Enter Message:").pack()
        self.chat_entry = tk.Entry(self.chat_entry_area_frame, width=60)
        self.chat_entry.bind("<Return>", lambda event: self.send_chat_message())
        self.chat_entry.bind("<Key>", lambda event: self.send_button.config(state=tk.NORMAL))
        self.chat_entry.pack(fill=tk.X)
        tk.Label(self.chat_entry_area_frame, text="Recipient Callsigns:").pack()
        self.recipients_entry = EntryWithPlaceholder(self.chat_entry_area_frame, width=60, placeholder="NOCALL,NO2CALL")
        self.recipients_entry.pack(fill=tk.X)
        self.recipients_entry.bind("<Return>", lambda event: self.send_chat_message())
        if self.settings.get('recipients'):
            self.recipients_entry.set(self.settings.get('recipients'))

        self.send_button = tk.Button(self.native_button_frame, text="Send", command=self.send_chat_message, state=tk.DISABLED)
        self.send_button.pack()
        

    def create_plugins_frame(self):
        self.plugins_canvas = tk.Canvas(self.top_section, bd=2, relief=tk.SUNKEN)
        
        self.plugins_frame = tk.Frame(self.plugins_canvas)
        self.plugins_frame_scrollbar = tk.Scrollbar(self.plugins_canvas, orient="vertical", command=self.plugins_canvas.yview)

        self.plugins_canvas.create_window((0, 0), window=self.plugins_frame, anchor="nw")
        self.plugins_canvas.configure(yscrollcommand=self.plugins_frame_scrollbar.set)

        # Bind a function to configure the scroll region of the canvas
        self.plugins_frame.bind("<Configure>", lambda e: self.plugins_canvas.configure(scrollregion=self.plugins_canvas.bbox("all")))

        self.plugins_frame_scrollbar.pack(side="right", fill="y")
        self.plugins_frame.pack(side="left", fill="both", expand=True, anchor="center")
        self.plugins_canvas.pack(side="left", fill="both", expand=True)
        # add a debug check box to the plugins frame
        self.debug_checkbutton = tk.Checkbutton(self.plugins_frame, text="Debug to Console", variable=self.debug)

        self.debug_checkbutton.pack()

        self.plugMgr.create_plugin_frames(self.plugins_frame)
        # add padding and basic style to all of the plugin frames
        for widget in self.plugins_frame.winfo_children():
            widget.pack_configure(pady=5)
            widget.config(bd=2, relief=tk.GROOVE)
            # add a separator between each plugin frame

    def create_transport_status_frame(self):
        # this will be updated by tk mainloop, and the selected transport will provide its contents
        self.transport_status_frame_holder = tk.Frame(self, bd=2, relief=tk.SUNKEN, height=50)
        self.transport_status_frame_holder.pack(fill=tk.X, expand=True)

    def create_widgets(self):
        self.create_menubar()
        self.top_section = tk.Frame(self)
        self.top_section.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        self.create_chat_frame()
        self.create_plugins_frame()
        self.create_transport_status_frame()

    def print_to_chatwindow(self, message: str, save=False):
        if not self.ui_ready.is_set():
            self.plugin_preload_messages.append(message)
            return
        self.message_box.config(state=tk.NORMAL)
        if self.plugin_preload_messages:
            [message for message in self.plugin_preload_messages if message]
            # filter out double newlines
            [message for message in self.plugin_preload_messages if message != '\n']
            for message in self.plugin_preload_messages:
                self.message_box.insert(tk.END, message+'\n')
            self.plugin_preload_messages = []
        self.message_box.insert(tk.END, message+'\n')
        if self.settings['use_message_history'] and save:
            self.message_history.append(message)
            # not sure if this works right.
            if len(self.message_history) > 500:
                self.message_history.pop(0)
        self.message_box.config(state=tk.DISABLED)
    
    def display_info_box(self):
        info_box = tk.Toplevel(self)
        info_box.title("About ARDOP Chat")
        info_box.geometry("500x300")
        version_label = tk.Label(info_box, text=f"Version: {self.version}")
        version_label.pack()
        info_label = tk.Label(info_box, text=info)
        info_label.pack()
        close_button = tk.Button(info_box, text="Close", command=info_box.destroy)
        close_button.pack()

    def display_warning_box(self, message):
        warning_box = tk.Toplevel(self)
        warning_box.title("Warning")
        warning_box.geometry("300x200")
        warning_label = tk.Label(warning_box, text=message)
        warning_label.pack()
        close_button = tk.Button(warning_box, text="Close", command=warning_box.destroy)
        close_button.pack()

    def get_recipients(self):
        recipients = self.recipients_entry.get().strip()
        if recipients == "NOCALL,NO2CALL":
            recipients = ""
        if not recipients:
            recipients = "ALL"
        return recipients

    def send_chat_message(self):
        message = self.chat_entry.get()
        sender = self.settings['callsign']
        recipients = self.get_recipients()
        # might move this into Core hamChatPlugin
        # If this was in a plugin, this format would be the same except for any
        # additional fields that the plugin would need to add to the header.
        # the next three lines would be basically the same.
        data = f"{sender}:chat:{self.version}:{recipients}:BEGIN:{message}:END:"
        if self.debug.get():
            print(f"Sending data: {data}")
        self.transport.append_bytes_to_buffer(data.encode())
        # do plugins want the data that we are sending? Probably not, for now.
        self.plugMgr.on_transmit_buffer()

        self.chat_entry.delete(0, tk.END)
        # for our message box
        self.print_to_chatwindow(f"{sender}->{recipients}({len(message)}): {message}", save=True)
        self.message_box.see(tk.END)
        self.send_button['state'] = 'disabled'
        self.save_message_history()

    def is_callsign(self, callsign: str) -> bool:
        # callsigns are 4-9 characters, plus an optional SSID which may be a - followed by a two digit number
        # minimum length is 4, maximum is 9
        callsign_in_header = callsign.split(':')[0]
        callsign_length = len(callsign_in_header)
        if callsign_length < 4 or callsign_length > 9:
            return False
        else:
            return True
    

    def has_hamChat_header(self, data: bytes) -> bool:
        # a hamChat header is a string that looks like this:
        # {sender}:{handler}:{version}:{recepients}:{optional multiple handler fields}:BEGIN:{data}:END:
        # example: N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
        # or for FileXfr: N0CALL:FileXfr:0.1:RECIPIENTS:FILENAME:FILESIZE:BEGIN:DATA:END:
        # the first four fields are always the same.
        if self.debug.get():
            print(f"Checking data for hamChat header: {data}")

        # split the header by the : character, and decode it to a string
        data_elements = data.decode().split(':')
        # is there a callsign in the first field?
        if not self.is_callsign(data_elements[0]):
            print(f"Invalid callsign: {data_elements[0]}")
            return False
        # does a second field exist with a string that is not empty?
        if not data_elements[1]:
            print(f"Invalid handler: {data_elements[1]}")
            return False
        # is the third field a single decimal point float version number?
        if not data_elements[2].split('.')[0].isdigit() or not data_elements[2].split('.')[1].isdigit():
            print(f"Invalid version: {data_elements[2]}")
            return False
        # is the fourth field a callsign or ALL?
        if not self.is_callsign(data_elements[3]) and data_elements[3] != "ALL":
            print(f"Invalid recipients: {data_elements[3]}")
            return False
        # Is there a BEGIN field?
        if not "BEGIN" in data_elements:
            print(f"No BEGIN field: {data_elements}")
            return False
        # Is there an END field?
        if not "END" in data_elements:
            print(f"No END field: {data_elements}")
            return False
        return True
        
    def listen_for_data(self):
        # this is run on its own thread
        while not self.die.is_set():
            try:
                # an annoying issue is if we start hamChat, and for example, ardop was already running and decoded some
                # data, that data is sitting in the incoming buffer. We can clear it out, or try to read it.
                if self.transport.is_ready():
                    data: bytes = self.transport.on_get_data()
                else:
                    time.sleep(0.325)
                    continue
            except OSError:
                # we are shutting down
                break
            # sometimes there is a timeout and we get a NoneType.
            if not data:
                continue
            if not self.has_hamChat_header(data):
                print(f"Nonstandard data: {data}")
                # this is nonstandard data, we will send it to the plugins to see if they can handle it
                # hopefully they can without crashing.
                self.plugMgr.on_payload_recieved(header=None, payload=data)
                continue

            # we have a hamChat header, let's parse it
            if self.debug.get():
                print(f"Received hamChat data: {data}")
            header = data.split(b':BEGIN:')[0]
            # log the contact in recent contacts
            sender = header.split(b":")[0].decode()
            timestamp = time.strftime("%H:%M:%S")
            # try to get frequency and mode from IPC
            # currently hardcoded to hamlib, but may change to a more generic rig control plugin (I am unaware of any other rig controls)
            # I don't like how there is both IPC and specially named hooks. This may be confusing to plugin developers,
            # because you can implement the same thing in two different ways. If plugins are to work with each other, they
            # should use IPC, not hooks. Hooks are for the main application to use, and maybe it should be the only one to use them.
            # I will think on this :^)
            freq: dict = self.plugMgr.IPC(target_plugin="Hamlib", from_plugin="hamChat", command="get_radio_frequency")
            mode: dict = self.plugMgr.IPC(target_plugin="Hamlib", from_plugin="hamChat", command="get_radio_mode")
            self.log_recently_heard(sender, timestamp, freq=freq.get('radio_frequency'), mode=mode.get('radio_mode'))
            # get everyting between :BEGIN: and :END:
            payload = data.split(b':BEGIN:')[1].split(b':END:')[0]

            # might move this block into Core hamChatPlugin
            # we handle chat in the main application, not in a plugin because the chat is integral to the program
            if b":chat:" in header:
                recipents = header.split(b":")[3].decode()
                message = f"{sender}->{recipents}: {payload.decode()}"
                self.print_to_chatwindow(message, save=True)
        
            self.plugMgr.on_payload_recieved(header=header, payload=payload)
            self.save_message_history()
        print("hamChat Data Listener Thread Exiting...")

    def update_ui_transport_state(self):
        # tell the currently selected transport to create or update its status frame.
        # the reason for this jankiness, is if the user switches to another transport,
        # we don't want the old transport's status frame in the transport status area.
        # maybe it would be better to do this as a UI event, but that would not work
        # if the transport is unable to connect to the radio or something.
        self.transport.on_ui_transport_status_frame(self.transport_status_frame_holder)
        self.plugMgr.update_plugin_frames()
        self.after(250, self.update_ui_transport_state)
    
    def update_transport_state_frame(self):
        while not self.die.is_set():
            self.transport.on_transport_state_update()
            time.sleep(0.25)
        print("hamChat Transport Status Frame Updater Thread Exiting...")

    def create_settings_menu(self):
        self.settings_menu = tk.Toplevel(self)
        self.settings_menu.title("Settings")
        self.settings_menu.geometry("300x300")

        # central frame for the two side-by-side columns
        # might be able to simplify later
        self.settings_frame = tk.Frame(self.settings_menu)

        # left side frame for user settings like callsign, gridsquare, etc.
        self.usersettings_frame = tk.Frame(self.settings_frame)

        self.callsign_label = tk.Label(self.usersettings_frame, text="Callsign")
        self.callsign_label.pack()
        self.callsign_entry = tk.Entry(self.usersettings_frame)
        self.callsign_entry.insert(0, self.settings['callsign'])
        self.callsign_entry.pack()

        self.gridsquare_label = tk.Label(self.usersettings_frame, text="Gridsquare")
        self.gridsquare_label.pack()
        self.gridsquare_entry = tk.Entry(self.usersettings_frame)
        self.gridsquare_entry.insert(0, self.settings['gridsquare'])
        self.gridsquare_entry.pack()

        # checkbox for enabling saving and loading of message history
        self.save_message_history_var = tk.IntVar()
        self.save_message_history_var.set(1)
        self.save_message_history_checkbutton = tk.Checkbutton(self.usersettings_frame, text="Save Message History", variable=self.save_message_history_var)
        self.save_message_history_checkbutton.pack()

        # button box frame
        self.settingsbuttons_frame = tk.Frame(self.settings_menu)
        self.save_button = tk.Button(self.settingsbuttons_frame, text="Save", command=self.save_settings)
        self.save_button.pack(side=tk.LEFT)
        self.cancel_button = tk.Button(self.settingsbuttons_frame, text="Cancel", command=self.settings_menu.destroy)
        self.cancel_button.pack(side=tk.RIGHT)

        self.settings_frame.pack()
        self.usersettings_frame.pack(side=tk.LEFT)
        # plugins will have their own settings menus and saving/loading them.
        # it's up to them to give themselves a button to open up their settings menu
        # if their settings can't fit in their plugin frame entry.
        self.settingsbuttons_frame.pack()

    def save_settings(self):
        self.settings['callsign'] = self.callsign_entry.get()
        self.settings['gridsquare'] = self.gridsquare_entry.get()
        self.settings['use_message_history'] = self.save_message_history_var.get()
        self.settings['recipients'] = self.recipients_entry.get()
        self._save_settings_to_file()
        self.print_to_chatwindow(f"Client Settings Updated" )
        self.settings_menu.destroy()
        # tell transports/plugins that we have new settings
        self.plugMgr.on_settings_update()

    def shutdown(self):
        print("Shutting Down...")
        self.plugMgr.on_clear_buffer()
        self.plugMgr.on_unkey_transmitter()
        self.die.set()
        self.plugMgr.on_shutdown() 
        sys.exit()

class EntryWithPlaceholder(tk.Entry):
    def __init__(self, master=None, placeholder="PLACEHOLDER", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.insert(0, self.placeholder)
        self.bind("<FocusIn>", self._clear_placeholder)

    def _clear_placeholder(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
    
    def set(self, text):
        self.delete(0, tk.END)
        self.insert(0, text)

if __name__ == '__main__':
    hamChatUI = HamChat()
    hamChatUI.mainloop()
