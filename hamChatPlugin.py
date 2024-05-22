import tkinter as tk
# uncomment when you use this template to create a new plugin
#from hamChatPlugin import hamChatPlugin

"""
hamChat features a standard header format. This is used to identify the sender,
the plugin, the version of the plugin, the recipients,
and the beginning and end of the payload. Plugin authors are able to add custom
fields to the header, but the standard fields should be present. This is so the data
can be routed to the correct plugin, and the plugin can identify the sender and recipients,
although it certainly adds significant overhead to short data transmissions.

Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

#class PluginName(hamChatPlugin):
class hamChatPlugin:
    def __init__(self, host_interface):
        """ This is the base class for all ARDOP Chat plugins, and provide a template for plugin authors."""

        self.header_id = ''
        self.info = """
        Plugins can be used to extend the functionality of the chat application
        to include new features, or to interact with the hamChat in new ways.
        Place a summary of the plugin here.
        """
        
        
        self.host_interface = host_interface
        # This allows us to interact with the main application's methods and variables.
        # Primarially, this is used to write messages to the main application's message box,
        # or to send data to other plugins via plugMgr

        self.definition = {
            'author': 'Author Name/Callsign',
            # the URL to the plugin's source code or documentation, most likely a github URL
            'url': 'https://github.com/Dinsmoor/hamChat',
            # this is very important, as it is used to route data to the correct plugin, and to identify the plugin
            # it must be unique, and should be the same as the name of the plugin class
            'name': 'Plugin Name',
            # this version string will be sent whenever you send a message from this plugin.
            # The valid format is MAJOR.PATCH, single digits.
            # Update MAJOR when you make a breaking change, PATCH when you make a non-breaking change,
            # such as a bugfix or interface change that will not break other plugins or affect communciation over the air.
            'version': '0.1',
            'description': self.info,
            # This is for specifying the transport the plugin provides, like 'ARDOP' or 'TCP'
            'transport': '',
            # this list is what tells the plugin manager to route data to this plugin.
            # if you want to parse all incoming data, include 'ALL'
            'handlers': [self.header_id],
            # if you talk to other plugins, you should specify them here, and their version as their behavior may change
            'depends_on': [{'plugin': 'Core', 'version': '0.1'}],
        }

        # Normally, we want our plugin to be quiet unless there is a critical error (do not print to console)
        # self.host_interface.debug.get() -> True/False
        # use like:
        # if self.host_interface.debug.get():
        #     print("The task has failed successfully.")
        # this ^ is how we can toggle output to console.

        # When we want to put text into the main chat window, such as alerting the user to something, we use this:
        # self.host_interface.print_to_chatwindow("Hello, World!", save=False)
        # If we want it to be persistent between sessions, we can set save=True (if the user has that setting enabled)

        # If we want to get some user settings, we can use this to access them
        # self.host_interface.settings.get('callsign')
        # self.host_interface.settings.get('gridsquare')
        
        # If we want to send data to another plugin, we can use this:
        # result = self.host_interface.plugMgr.IPC('PluginName', 'FromPluginName', 'COMMAND', b'DATA')
        # This will return True if the command was successful, False if it was not.
        # This is EXPERIMENTAL and it is up to the plugin author to support this interface.

        # If we want to get whatever transport the user currently has selected, we can use this:
        # transport = self.host_interface.get_selected_transport()
        # This is the actual transport object, exposing the methods and variables of the transport.
        # use with caution! This gives you great power, but it's up to you to use it wisely.

        # If we want to send data to the current transport, we can use this:
        # self.host_interface.plugMgr.append_bytes_to_buffer(b'DATA')
        # or
        # self.host_interface.transport.append_bytes_to_buffer(b'DATA')
        # This will append the data to the current transport's buffer, and it will be sent when the transport is commanded to send it.

        # if we want to to key or unkey the transmitter (if there is sufficent rig control), we can use this:
        # self.host_interface.transport.on_key_transmitter()
        # self.host_interface.transport.on_unkey_transmitter()


    def on_payload_recieved(self, data: dict):
        '''This method is called by the main application when a data frame is received from the selected transport.

        In your plugin, this is where you would handle incoming data that you have registered as a handler for.

        It is a dictionary containing any hamChat header and the payload.
        If you use "ALL" in your handlers, you may recieve nonstandard data, containing only a payload.

        When it gets here, it will be a dictionary like this:
        {'header': b'SENDER:PLUGINNAME:PLUGINVERSION:RECIPENTS:BEGIN:', 'payload': b'<DATA>'}
        '''
        pass
    
    def on_command_received(self, command: str):
        '''This method is called when a command response is received from the current transport.
        Plugins can use this to see traffic back from the selected transport.
        Be careful while using this, if your processing is blocking/takes a long time.
        It may interfere with the transport.
        If I don't see a use for this (currently it's just a liability), I may remove it in the future.'''
        pass
    
    def on_transmit_buffer(self):
        '''This method is called when the selected transport is told to send its buffer.
        Transport plugins should implement this method to send their data.
        Plugins that send data should call this method after loading their data into the buffer. 
        '''
        pass
    
    def on_clear_buffer(self):
        '''This method is for clearing the data buffer of the selected transport.'''
        pass
    
    def on_key_transmitter(self):
        '''This method is called when a transport wants to key the transmitter.
        Plugins that control radios should implement this method.
        Plugins that want to key the transmitter should call this method in their application code.'''
        pass
    
    def on_unkey_transmitter(self):
        '''This method is called when a transport wants to unkey the transmitter.
        Plugins that control radios should implement this method.
        Plugins that want to unkey the transmitter should call this method in their application code.'''
        pass
    
    def create_plugin_frame(self, tkParent) -> tk.Frame:
        '''This method is where a plugin can create its own options buttons on the right scrollbar
        in the main application. See other plugins for examples.'''
        pass

    def on_transport_state_update(self):
        '''This method is called regularly by the main application to update the transport state, as a
        convenience feature if they don't want to implement their own thread task to do so.
        This is not on the main thread, and cannot be used to update the UI elements or it will
        trigger a RuntimeError because of a limitation of Tkinter.'''
        pass

    def append_bytes_to_buffer(self, data: bytes):
        '''This method is called when the plugin is asked to append data to the selected transport's buffer.
        If you are writing a transport plugin, this is where you would receive bytes to send by implementing this hook.
        If you are writing a plugin that sends data, you would call this in your application code to send data to the current transport.
        '''
        pass

    def on_ui_transport_status_frame(self, tkParent) -> tk.Frame:
        '''This method is called when the main application wants to display the transport status.
        This is where you would create a frame to display the status of your transport plugin,
        or update the tk variables that are used to display the status of your transport plugin.'''
        pass
    
    def on_get_data(self) -> bytes:
        '''This method is called when the plugin is asked to return data from the buffer.
        Plugins providing a transport must implement this method.
        The return value is expected to be bytes, absent any length
        or modem-specific headers, like FECFEC for ARDOP.'''
        pass
    
    def on_shutdown(self):  
        '''This method is called when the program is being shut down.
        Plugins should always implement this method to clean up any resources they have allocated,
        like sockets, files, or other resources.'''
        pass

    def on_settings_update(self):
        '''This method is called when the settings are updated.
        This is where you might update/save your plugin's settings.
        Since plugins are likely to implement tk widgets with tk variables,
        it would be wise to declare them beforehand with defaults (or load any defaults)
        in __init__ and update them here.'''
        pass

    def IPC(self, target_plugin: str, from_plugin: str, command: str, data: bytes = None) -> bool:
        '''This method is called when a plugin wants to send an inter-plugin command.
        This is an EXPERIMENTAL way how plugins can communicate with each other,
        by sending commands to each other.
        The target_plugin is the name of the plugin you want to send the command to, by name.
        The from_plugin is the name of the plugin that is sending the command, please specify name.
        The command is the command you want to send to the target plugin.
        The data is the data you want to send to the target plugin, if any.
        This should return True if the command was successful, False if it was not.
        It is up to the plugin author to support this interface'''
        pass