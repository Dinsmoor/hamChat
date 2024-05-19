import sys
import os
import importlib.util
# assist with type hinting
from ARDOPCFPlugin import ARDOPCFPlugin

class PluginManager:
    def __init__(self, host_interface, plugin_folder='ARDOPCF_Plugins'):
        '''This class is used to manage the plugins that are loaded into the ARDOP Chat application.'''

        # contains like: [ARDOPCFPluginCore, ARDOPCFPluginFileTransfer] objects
        # currently there is no load order except alphabetical
        self.plugins: list[ARDOPCFPlugin] = []
        self.host_interface = host_interface

        if not os.path.exists(plugin_folder):
            os.makedirs(plugin_folder)

        # add the plugin folder to the system path in order to import the plugins
        sys.path.append(plugin_folder)
        self.load_plugins(plugin_folder)
        self.unmet_dependencies = []
        if not self.are_dependencies_satisfied():
            unmet = ', '.join(self.unmet_dependencies)
            print("WARNING: Plugin dependencies not satisfied.")
            print("You may encounter unexpected behavior.")
            print(f"Unmet dependencies: {unmet}")
            self.host_interface.display_warning_box(f"Plugin dependencies not satisfied: {unmet}")
        self.list_plugins()

    def load_plugins(self, plugin_folder):
        # These variables could use some renaming to make it more clear
        filename: str
        for filename in os.listdir(plugin_folder):
            if filename.endswith('.py'):
                spec = importlib.util.spec_from_file_location(filename[:-3], os.path.join(plugin_folder, filename))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    if attr_name != 'ARDOPCFPlugin':
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, ARDOPCFPlugin):
                            valid_plugin_object = attr(host_interface=self.host_interface)
                            self.plugins.append(valid_plugin_object)

    def are_dependencies_satisfied(self):
        plugin: ARDOPCFPlugin
        for plugin in self.plugins:
            dependency: dict
            for dependency in plugin.definition.get('depends_on'):
                if not self.is_dependency_met(dependency.get('plugin'), dependency.get('version')):
                    print(f"Dependency NOT met for {plugin.definition.get('name')}: {dependency.get('plugin')} {dependency.get('version')}")
                    self.unmet_dependencies.append(f"{dependency.get('plugin')} {dependency.get('version')}")
                    return False
        return True
    
    def is_dependency_met(self, plugin_name: str, version: str):
        plugin: ARDOPCFPlugin
        for plugin in self.plugins:
            if plugin.definition.get('name') == plugin_name:
                if plugin.definition.get('version') != version:
                    return False
        return True

    def list_plugins(self):
        print(f"{len(self.plugins)} Loaded plugins:")
        for plugin in self.plugins:
            print(f"{plugin.definition.get('name')}:{plugin.definition.get('version')} by {plugin.definition.get('author')}")
            print(plugin.info)


    def on_data_received(self, header, payload):
        '''Only plugins that declare a handler for the protocol_identifier in the data will receive it.'''
        for plugin in self.plugins:
            send_to_plugin = False
            for handler in plugin.definition['handlers']:
                # some plugins want to listen to all data, some only to specific data
                if handler == 'ALL':
                    send_to_plugin = True
                elif handler in header.split(b':')[1].decode():
                    remote_plugin_version = header.split(b':')[2].decode()
                    if plugin.definition['version'] != remote_plugin_version:
                        self.host_interface.display_warning_box(f'''Local plugin {plugin.definition.get("name")} has version mismatch
                                                with remote plugin {remote_plugin_version}.\n 
                                                Data may not be handled correctly.''')
                    # we have a plugin that can handle this data, it will do
                    # whatever in this interface it needs to do without further handling here.
                    send_to_plugin = True
            if send_to_plugin:
                plugin.on_data_received({'header': header, 'payload': payload})
    
    def on_command_received(self, command: str):
        for plugin in self.plugins:
            plugin.on_command_received(command)

    def on_data_loaded_into_buffer(self, data: bytes):
        for plugin in self.plugins:
            plugin.on_data_loaded_into_buffer(data)
    
    def on_transmit_buffer(self):
        for plugin in self.plugins:
            plugin.on_transmit_buffer()
    
    def on_clear_buffer(self):
        for plugin in self.plugins:
            plugin.on_clear_buffer()

    def on_key_transmitter(self):
        for plugin in self.plugins:
            plugin.on_key_transmitter()
    
    def on_unkey_transmitter(self):
        for plugin in self.plugins:
            plugin.on_unkey_transmitter()
    
    def on_ui_create_settings_menu(self):
        for plugin in self.plugins:
            plugin.on_ui_create_settings_menu()
    
    def on_ui_save_settings(self):
        for plugin in self.plugins:
            plugin.on_ui_save_settings()

    def on_ui_create_widgets(self):
        for plugin in self.plugins:
            plugin.on_ui_create_widgets()
    
    def on_ui_ardop_state_update(self):
        for plugin in self.plugins:
            plugin.on_ui_ardop_state_update()
    
    def on_shutdown(self):
        for plugin in self.plugins:
            plugin.on_shutdown()
