import tkinter as tk
from hamChatPlugin import hamChatPlugin
import time
import threading
"""
Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

class Beacon(hamChatPlugin):
    def __init__(self, host_interface):
        self.info = """
        When enabled, this plugin will continuously send predefined chat messages
        with optional identifiers at predefined intervals.
        https://github.com/Dinsmoor/hamChat
        """
        
        
        self.host_interface = host_interface

        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'url': 'https://github.com/Dinsmoor/hamChat',
            'name': 'Beacon',
            'version': '0.1',
            'description': self.info,
            'transport': '',
            'handlers': [],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
        self.enabled = tk.BooleanVar()
        self.interval = tk.IntVar()
        self.interval.set(30)
        self.message = tk.StringVar()
        self.message.set("Beacon from hamChat!")
        self.include_interval = tk.BooleanVar()
        self.enabled.set(False)
        self.enable_checkbox = tk.Checkbutton()
        self.stop_event = threading.Event()

        self.sender_thread = threading.Thread(target=self.send_beacon)
        self.sender_thread.start()

    def send_beacon(self):
        # this will run in a separate thread
        now = time.time()
        while self.stop_event.is_set() == False:
            if self.enabled.get() and (time.time() - now > self.interval.get()):
                callsign = self.host_interface.settings['callsign']
                recipients = self.host_interface.get_recipients()
                message = self.message.get()
                print(f"Sending Beacon: {message}")
                self.host_interface.transport.append_bytes_to_buffer(f"{callsign}:chat:0.1:{recipients}:BEGIN:{message}:END:".encode())
                self.host_interface.transport.on_transmit_buffer()
                now = time.time()
            # this allows us to shut down this thread quickly without wasting resources
            time.sleep(0.5)

    def show_settings_window(self):
        menu_item_window = tk.Toplevel()
        menu_item_window.title("Beacon Settings")
        menu_item_window.geometry("300x300")
        configure_area = tk.Frame(menu_item_window)
        enable_checkbox = tk.Checkbutton(configure_area, text="Enable", variable=self.enabled)
        enable_checkbox.pack()
        interval_label = tk.Label(configure_area, text="Interval (10-1800 seconds)")
        interval_label.pack()
        interval_spinbox = tk.Spinbox(configure_area, from_=10, to=1800, textvariable=self.interval)
        interval_spinbox.pack()
        message_label = tk.Label(configure_area, text="Message")
        message_label.pack()
        message_entry = tk.Entry(configure_area, textvariable=self.message)
        message_entry.pack()
        button_area = tk.Frame(configure_area)
        save_button = tk.Button(button_area, text="Save", command=menu_item_window.destroy)
        save_button.pack()
        configure_area.pack()

    def create_plugin_frame(self, tkParent) -> tk.Frame:
        beacon_frame = tk.Frame(tkParent)
        title = tk.Label(beacon_frame, text="Beacon")
        title.pack()
        enable_checkbox = tk.Checkbutton(beacon_frame, text="Enable", variable=self.enabled)
        enable_checkbox.pack()
        self.configure_button = tk.Button(beacon_frame, text="Configure", command=self.show_settings_window)
        self.configure_button.pack()
        beacon_frame.pack()
        return beacon_frame
    
    def on_shutdown(self):
        self.stop_event.set()