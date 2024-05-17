class ARDOPCFPlugin:
    def __init__(self, host_interface):
        """ This is the base class for all ARDOP Chat plugins."""

        self.info = """
        Plugins can be used to extend the functionality of the chat application
        to include new features, or to interact with the ARDOPC client in new ways.
        Place a summary of the plugin here.
        """
        
        
        self.host_interface = host_interface
        """
        This allows us to interact with the main application.

        For example, to send a command directly to the TNC and await a response, you can use:
        self.host_interface.ardop.cmd_response(command='', wait=True)
        """

        self.definition = {
            'author': 'Author Name/Callsign',
            'name': 'Plugin Name',
            # this version string will be sent whenever you send a message from this plugin.
            # it should be kept short.
            'version': '0.1',
            'description': self.info,
            # this is what tells the plugin manager to route data to this plugin
            'protocol_identifier': 'TemPlate',
            'handlers': ['TemPlate', 'PROTOCOL_IDENTIFIER2', 'PROTOCOL_IDENTIFIER3'],
            'expected_header': "CALLSIGN:TemPlate:0.1:BEGIN:", # just so it's clear what the header should look like
            'provides': self.__class__.__name__,
            'depends_on': [{'plugin': 'PluginName', 'version': '0.1'}],
        }

    def on_data_received(self):
        '''This method is called when a data frame is received from the TNC, after removing the ARDOP header.
        It is a dictionary split between the header and the payload.
        This should get here like this: header = b'CALLSIGN:PLUGINNAME:PLUGINVERSION:' payload = b'<DATA>'
        The main use is to look at the data and determine if it needs to be processed by this plugin.'''
        pass
    
    def on_command_received(self):
        '''This method is called when a command is received from the TNC, you get a copy'''
        pass
    
    def on_unhandled_command_received(self):
        '''This method is called when a command is received from the TNC that is not handled by the core plugin.'''
        pass
    
    def on_data_loaded_into_buffer(self):
        '''This method is called after data is loaded into the TNC buffer.'''
        pass

    def on_file_loaded_into_buffer(self):
        '''This method is called before a file is read and loaded into the TNC buffer.
        You can use this to modify the file before it is loaded into the buffer.'''
        pass
    
    def on_file_saved_to_disk(self):
        '''This method is called before a file is saved to disk.
        You can use this to modify the file before it is saved to disk.'''
        pass
    
    def on_transmit_buffer(self):
        '''This method is called when the TNC buffer is commanded to be transmitted'''
        pass
    
    def on_clear_buffer(self):
        '''This method is called when the TNC buffer is cleared'''
        pass
    
    def on_key_transmitter(self):
        '''This method is called when the TNC is keyed'''
        pass
    
    def on_unkey_transmitter(self):
        '''This method is called when the TNC is unkeyed.'''
        pass
    
    def on_initialize(self):
        '''This method is called when the TNC is initialized.'''
        pass
    
    def on_ui_create_settings_menu(self):
        '''This method is called when the settings menu is created.
        This is where the plugin can add any settings that it needs to the settings menu.'''
        pass
    
    def on_ui_save_settings(self) -> dict:
        '''This method is called when the user saves the settings in the settings menu.
        This is where the plugin return any settings that it needs to save.'''
        pass
    
    def on_ui_create_widgets(self):
        '''This method is called when the plugin is loaded to create any widgets
        that the plugin may need to interact with the user.
        usage example:
        self.ui = tk.Toplevel(self.host_interface)
        self.ui.title("Plugin Name")
        self.ui.geometry("300x300")
        self.label = tk.Label(self.ui, text="Plugin Label")
        self.label.pack()
        etc...'''
        pass

    def on_plugin_enabled(self):
        '''Plugins are dynamically loaded and unloaded, so this method
        is called when the plugin is enabled'''
        pass

    def on_plugin_disabled(self):
        '''Plugins are dynamically loaded and unloaded, so this method
        is called when the plugin is disabled'''
        pass

    def on_ui_ardop_state_update(self):
        '''This method is called when the ARDOP state is updated, usually every 200 ms
        Use this to update any UI elements that need to be updated with the ARDOP state or
        with your plugin state.'''
        pass
    