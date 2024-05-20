import tkinter as tk

class hamChatPlugin:
    def __init__(self, host_interface):
        """ This is the base class for all ARDOP Chat plugins."""

        self.header_id = ''
        self.info = """
        Plugins can be used to extend the functionality of the chat application
        to include new features, or to interact with the ARDOPC client in new ways.
        Place a summary of the plugin here.
        https://github.com/Dinsmoor/hamChat
        """
        
        
        self.host_interface = host_interface
        """
        This allows us to interact with the main application's methods and variables.
        Primarially, this is used to write messages to the main application's message box,
        or to send data to other plugins via plugMgr
        """

        self.definition = {
            'author': 'Author Name/Callsign',
            'url': '',
            'name': 'Plugin Name',
            # this version string will be sent whenever you send a message from this plugin.
            # it should be kept short, as it will be used in the interface
            'version': '0.1',
            'description': self.info,
            # This is for specifying the transport the plugin provides, like 'ARDOP' or 'TCP'
            'transport': '',
            # this is what tells the plugin manager to route data to this plugin
            'handlers': [self.header_id],
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }

    def on_payload_recieved(self, data: dict):
        '''This method is called when a data frame is received from the selected transport.

        In your plugin, this is where you would handle incoming data that you have registered as a handler for.

        It is a dictionary containing the hamChat header and the payload.
        If you use "ALL" in your handlers, you may recieve nonstandard data, you will have to deal with a Nonetype header
        and the payload yourself. 

        A typical hamChat frame will look like this:
        header = b'SENDER:PLUGINNAME:PLUGINVERSION:RECIPENTS:BEGIN:' payload = b'<DATA>:END:'
        '''
        pass
    
    def on_command_received(self, command: str):
        '''This method is called when a command is received from the current transport.
        Plugins can use this to see traffic back from the selected transport.
        Be careful while using this, if your processing is blocking/takes a long time.
        It may interfere with the transport.'''
        pass
    
    def on_data_loaded_into_buffer(self, data: bytes):
        '''Transports can call this method to notify other plugins that data has been loaded into the buffer,
        with a copy of that data. '''
        pass
    
    def on_transmit_buffer(self):
        '''This method is called when the transport buffer is commanded to be transmitted by the host application.
        This is where transports would try to send their data, or plugins that send data would call the transport to send it
        by: self.host_interface.plugMgr.on_transmit_buffer()'''
        pass
    
    def on_clear_buffer(self):
        '''This method is for clearing the buffer of the selected transport.
        '''
        pass
    
    def on_key_transmitter(self):
        '''This method is called when a transport wants to key the transmitter.'''
        pass
    
    def on_unkey_transmitter(self):
        '''This method is called when a transport wants to unkey the transmitter.'''
        pass
    
    def create_plugin_frame(self, tkParent) -> tk.Frame:
        '''This method is called when the plugin is asked to create their
        buttons and widgets in the plugin scroll frame.'''
        pass

    def on_transport_state_update(self):
        '''This method is called when the selected transport state needs to be updated.
        This is useful if your transport needs to regularly update UI variables,
        like a status label in the transport status frame.'''
        pass

    def append_bytes_to_buffer(self, data: bytes):
        '''This method is called when the plugin is asked to append data to the selected transport's buffer.
        If you are writing a transport plugin, this is where you would receive bytes to send by implementing this hook.
        If you are writing a plugin that sends data, you would call this in your application code to send data to the current transport.
        by: self.host_interface.plugMgr.append_bytes_to_buffer(data)'''
        pass

    def on_ui_transport_status_frame(self, tkParent) -> tk.Frame:
        '''This method is called when the UI needs to update the transport state.'''
        pass
    
    def on_get_data(self) -> bytes:
        '''This method is called when the plugin is asked to get data from the buffer.
        Applies only to transport plugins.'''
        pass
    
    def on_shutdown(self):  
        '''This method is called when the program is being shut down.'''
        pass
    
    def on_estimate_time_to_send(self, datalen: int) -> float:
        '''This method is called to estimate the time it will take to send the data.
        It should return the time in seconds it will take to send the data currently
        in the buffer, or that has yet to be loaded into the buffer.'''
        pass

    def on_settings_update(self):
        '''This method is called when the settings are updated.
        This is where you would update/save your plugin's settings.'''
        pass