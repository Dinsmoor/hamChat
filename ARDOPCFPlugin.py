
class ARDOPCFPlugin:
    def __init__(self, host_interface):
        self.info = """
        This is a template for a plugin for the ARDOP Chat application.
        Plugins can be used to extend the functionality of the chat application
        to include new features, or to interact with the ARDOPC client in new ways.
        Place a summary of the plugin here.
        """
        
        """
        this allows us to read attributes from the host interface
        such as the state of the TNC or the state of the application
        and allows for more complex interactions with the TNC at the discretion of the author.

        For example, to send a command directly to the TNC and await a response, you can use:
        host_interface.cmd_response(command='', wait=True)
        Please note that this will block the main thread until a response is received, so use with caution.
        Also note that the response may not be complete or return on this thread
        because there is another very important thread that listens for responses.
        """
        self.host_interface = super(host_interface)

        """
        This is used tp extends the core plugin's protocol fields of callsign and plugin name.
        The core plugin protocol format is:
        CALLSIGN:PLUGINNAME:PLUGINVERSION:BEGIN:DATA
        But you can insert additional fields in between PLUGINVERSION and BEGIN, if they
        are specified here in protocol_fields.
        Colons are used as delimiters, but you can include them in the data, as we only split
        the data until we see the BEGIN field, which is just "BEGIN".
        """
        self.plugin_definition = {
            'author': 'Author Name/Callsign',
            'name': 'Plugin Name',
            # this version string will be sent whenever you send a message from this plugin.
            # it should be kept short.
            'version': '0.1',
            'description': self.info,
            # this is what tells the plugin manager to route data to this plugin
            'protocol_identifier': 'TEMPLATE',
            # this is where you can define any additional fields that the plugin needs
            # they are in order, and you must specify the type of data that is expected
            'protocol_fields': [{'field_name': 'FIELDNAME', 'field_type': str},
                                {'field_name': 'FIELDNAME2', 'field_type': int},] 
        }

    def on_data_received(self, data : bytes) -> bytes:
        '''This method is called when a data frame is received from the TNC, after removing the ARDOP header.
        This should look like b'CALLSIGN:PLUGINNAME:PLUGINVERSION:BEGIN:<DATA>'
        The main use is to look at the data and determine if it needs to be processed by this plugin.'''
        raise NotImplementedError
    
    def on_command_received(self, command : str) -> str:
        '''This method is called when a command is received from the TNC, you get a copy'''
        raise NotImplementedError
    
    def on_unhandled_command_received(self, command : str) -> None:
        '''This method is called when a command is received from the TNC that is not handled by the core plugin.'''
        raise NotImplementedError
    
    def on_data_loaded_into_buffer(self, data : bytes):
        '''This method is called after data is loaded into the TNC buffer.'''
        raise NotImplementedError

    def on_file_loaded_into_buffer(self, filename : str) -> bytes:
        '''This method is called before a file is read and loaded into the TNC buffer.
        You can use this to modify the file before it is loaded into the buffer.'''
        raise NotImplementedError
    
    def on_file_saved_to_disk(self, filedata : bytes) -> bytes:
        '''This method is called before a file is saved to disk.
        You can use this to modify the file before it is saved to disk.'''
        raise NotImplementedError
    
    def on_transmit_buffer(self):
        '''This method is called when the TNC buffer is commanded to be transmitted'''
        raise NotImplementedError
    
    def on_clear_buffer(self):
        '''This method is called when the TNC buffer is cleared'''
        raise NotImplementedError
    
    def on_key_transmitter(self):
        '''This method is called when the TNC is keyed'''
        raise NotImplementedError
    
    def on_unkey_transmitter(self):
        '''This method is called when the TNC is unkeyed.'''
        raise NotImplementedError
    
    def on_initialize(self):
        '''This method is called when the TNC is initialized.'''
        raise NotImplementedError
    
    def on_ui_create_settings_menu(self):
        '''This method is called when the settings menu is created.
        This is where the plugin can add any settings that it needs to the settings menu.'''
        raise NotImplementedError
    
    def on_ui_save_settings(self) -> dict:
        '''This method is called when the user saves the settings in the settings menu.
        This is where the plugin return any settings that it needs to save.'''
        raise NotImplementedError
    
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
        raise NotImplementedError

    def on_plugin_enabled(self):
        '''Plugins are dynamically loaded and unloaded, so this method
        is called when the plugin is enabled'''
        raise NotImplementedError

    def on_plugin_disabled(self):
        '''Plugins are dynamically loaded and unloaded, so this method
        is called when the plugin is disabled'''
        raise NotImplementedError
    