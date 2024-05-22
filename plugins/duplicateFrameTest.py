import tkinter as tk
from hamChatPlugin import hamChatPlugin
import time
import threading
"""
Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

class duplicateFrameTest(hamChatPlugin):
    def __init__(self, host_interface):
        self.info = """
        When enabled, this plugin will continuously send chat messages with incrementing numbers.
        This is used for testing ardop for duplicate frame errors.
        https://github.com/Dinsmoor/hamChat
        """
        
        
        self.host_interface = host_interface

        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'url': 'https://github.com/Dinsmoor/hamChat',
            'name': 'duplicateFrameTest',
            'version': '0.1',
            'description': self.info,
            'transport': '',
            'handlers': ['ALL'],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
        self.enabled = tk.BooleanVar()
        self.enabled.set(False)
        self.enable_checkbox = tk.Checkbutton()
        self.stop_event = threading.Event()

        self.sender_thread = threading.Thread(target=self.send_chat_messages)
        self.sender_thread.start()

    def send_chat_messages(self):
        # this will run in a separate thread
        message_number = 0
        now = time.time()
        while self.stop_event.is_set() == False:
            if self.enabled.get() and (time.time() - now > 10):
                message_number += 1
                callsign = self.host_interface.settings['callsign']
                recipients = self.host_interface.get_recipients()
                self.host_interface.transport.append_bytes_to_buffer(f"{callsign}:chat:0.1:{recipients}:BEGIN:TF#{message_number}:END:".encode())
                self.host_interface.print_to_chatwindow(f"Sent TF#{message_number} to {recipients}")
                self.host_interface.transport.on_transmit_buffer()
                now = time.time()
            # this allows us to shut down this thread quickly without wasting resources
            time.sleep(0.1)


    def create_plugin_frame(self, tkParent) -> tk.Frame:
        self.autoack_frame = tk.Frame(tkParent)
        self.enable_checkbox = tk.Checkbutton(self.autoack_frame, text="Enable duplicateFrameTest", variable=self.enabled)
        self.enable_checkbox.pack()
        self.autoack_frame.pack()
        return self.autoack_frame
    
    def on_shutdown(self):
        self.stop_event.set()