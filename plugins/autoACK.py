import tkinter as tk
from hamChatPlugin import hamChatPlugin
import time
"""
Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

class autoACK(hamChatPlugin):
    def __init__(self, host_interface):
        """ This is the base class for all ARDOP Chat plugins."""
        self.info = """
        This plugin automatically sends an ACK chat message in response
        if we recieve any payload with a standard hamChat header.
        https://github.com/Dinsmoor/hamChat
        """
        
        
        self.host_interface = host_interface

        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'url': 'https://github.com/Dinsmoor/hamChat',
            'name': 'autoACK',
            'version': '0.1',
            'description': self.info,
            'transport': '',
            'handlers': ['ALL'],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }
        self.enabled = tk.BooleanVar()
        self.enabled.set(False)
        self.enable_checkbox = tk.Checkbutton()
        self.reply_to_all = tk.BooleanVar()
        self.reply_to_all.set(False)
        self.reply_to_all_checkbox = tk.Checkbutton()
        
    def on_payload_recieved(self, data: dict):
        # we do not care about nonstandard data, only hamchat data
        if not self.enabled.get():
            return
        if not data['header']:
            return
        # we do not want to ACK our own ACKs
        # it'd be an ACK ATTACK!
        if b"autoACKed " in data['payload'][:10]:
            return
        recepients = data['header'].split(b':')[3]
        our_callsign = self.host_interface.settings['callsign'].encode()

        # spometimes we will get an ack back, sometimes not!
        # right now does not respect SSID
        if (our_callsign in recepients) or self.reply_to_all.get():
            if self.host_interface.debug.get():
                print(f"autoACK: Responding to {recepients} with ACK")

            length_of_data = len(data['payload'])
            ack = f"{our_callsign.decode()}:chat:0.1:{data['header'].split(b':')[0].decode()}:BEGIN:autoACKed {length_of_data} bytes:END:".encode()
            # up to the transport to determine if the channel is busy or not.
            self.host_interface.transport.append_bytes_to_buffer(ack)
            # wait a moment before sending the ACK in return, the data interface may not be ready yet 
            time.sleep(0.1)
            self.host_interface.transport.on_transmit_buffer()

    def create_plugin_frame(self, tkParent) -> tk.Frame:
        self.autoack_frame = tk.Frame(tkParent)
        self.enable_checkbox = tk.Checkbutton(self.autoack_frame, text="Enable autoACK", variable=self.enabled)
        self.enable_checkbox.pack()
        self.reply_to_all_checkbox = tk.Checkbutton(self.autoack_frame, text="ACK to all", variable=self.reply_to_all)
        self.reply_to_all_checkbox.pack()
        self.autoack_frame.pack()
        return self.autoack_frame