from ..ARDOPCFPlugin import ARDOPCFPlugin

class ARDOPCFPluginChat(ARDOPCFPlugin):
    def __init__(self):
        self.info = """
        This is the main plugin for the ARDOP Chat application.
        The main plugin provides the basic functionality of the chat application,
        such as sending and receiving UTF-8 messages.
        """
        self.plugin_definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Text Chat',
            'version': '0.1',
            'description': self.info,
            'protocol_identifier': 'CHAT',
            # this is where you can define any additional fields that the plugin needs
            # they are in order, and you must specify the type of data that is expected
            'protocol_fields': [{'field_name': 'TO', 'field_type': str}, # optional callsign of the recipient
                                ] 
        }
    
    def on_data_received(self, data):
        pass
    
    def on_command_received(self, command):
        pass
    
    def on_data_loaded_into_buffer(self, data):
        pass
    
    def on_file_loaded_into_buffer(self, filename):
        pass
    
    def on_file_saved_to_disk(self, filename):
        pass
    
    def on_transmit_buffer(self):
        pass
    
    def on_clear_buffer(self):
        pass
    
    def on_key_transmitter(self):
        pass
    
    def on_unkey_transmitter(self):
        pass
    
    def on_initialize(self):
        pass
    
    def on_ui_create_settings_menu(self):
        pass
    
    def on_ui_save_settings(self):
        pass
    
    def on_ui_create_widgets(self):
        pass
