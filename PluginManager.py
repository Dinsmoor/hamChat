import sys
import os
import importlib.util
# assist with type hinting
from hamChatPlugin import hamChatPlugin
import tkinter as tk

class PluginManager:
    def __init__(self, host_interface, plugin_folder='plugins'):
        '''This class is used to manage the plugins that are loaded into the ARDOP Chat application.'''

        # contains like: [Core, FileTransfer, Hamlib, ARDOPCF] objects
        # currently there is no load order except whatever os.listdir gives us
        self.plugins = [] # type: list[hamChatPlugin]
        self.transports = [] # type: list[str]
        self.host_interface = host_interface

        if not os.path.exists(plugin_folder):
            os.makedirs(plugin_folder)
        # add the plugin folder to the system path in order to import the plugins when load_plugins is called
        sys.path.append(plugin_folder)

    def load_plugins(self, plugin_folder):        
        self.__load_plugins(plugin_folder)

        self.unmet_dependencies = []
        if not self.are_dependencies_satisfied():
            unmet = ', '.join(self.unmet_dependencies)
            print("WARNING: Plugin dependencies not satisfied.")
            print("You may encounter unexpected behavior.")
            print(f"Unmet dependencies: {unmet}")
            self.host_interface.display_warning_box(f"Plugin dependencies not satisfied: {unmet}")

        self.list_plugins()
        self.register_transports()

    def __load_plugins(self, plugin_folder):
        # These variables could use some renaming to make it more clear
        # What we're doing is looking for .py files in the plugin folder, finding out if they are a subclass of hamChatPlugin
        # and if they are, we instantiate them and add them to the list of plugins.
        # we also filter out the hamChatPlugin class itself, as it is not a plugin, but a base class.
        filename: str
        for filename in os.listdir(plugin_folder):
            if filename.endswith('.py'):
                spec = importlib.util.spec_from_file_location(filename[:-3], os.path.join(plugin_folder, filename))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    if attr_name != 'hamChatPlugin':
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, hamChatPlugin):
                            valid_plugin_object = attr(host_interface=self.host_interface)
                            self.plugins.append(valid_plugin_object)

    def are_dependencies_satisfied(self):
        plugin: hamChatPlugin
        for plugin in self.plugins:
            dependency: dict
            for dependency in plugin.definition.get('depends_on'):
                if not self.is_dependency_met(dependency.get('plugin'), dependency.get('version')):
                    print(f"Dependency NOT met for {plugin.definition.get('name')}: {dependency.get('plugin')} {dependency.get('version')}")
                    self.unmet_dependencies.append(f"{dependency.get('plugin')} {dependency.get('version')}")
                    return False
        return True
    
    def is_dependency_met(self, plugin_name: str, version: str):
        plugin: hamChatPlugin
        for plugin in self.plugins:
            if plugin.definition.get('name') == plugin_name:
                if plugin.definition.get('version') != version:
                    return False
        return True

    def register_transports(self):
        for plugin in self.plugins:
            if plugin.definition.get('transport'):
                self.transports.append(plugin.definition.get('transport'))
        print(f"{len(self.transports)} Loaded transports: {self.transports}")

    def list_plugins(self):
        print(f"{len(self.plugins)} Loaded plugins:")
        for plugin in self.plugins:
            print(f"{plugin.definition.get('name')}:{plugin.definition.get('version')} by {plugin.definition.get('author')}")
            print(plugin.info)

    def __plugin_exception(self, method_called, plugin, exception, extra_info=None):
        message = f"Plugin {plugin.definition.get('name')} had an exception: {exception}"
        if extra_info:
            message += f"\n{extra_info}"
        self.host_interface.display_warning_box(message)
        print(message)
        # if we are in debug mode, we will print the traceback
        if self.host_interface.settings.get('debug'):
            print(f"Traceback: {sys.exc_info()[2]}")
            raise


    def on_payload_recieved(self, header, payload):
        '''Only plugins that declare a handler for the data will receive it.'''
        for plugin in self.plugins:
            send_to_plugin = False
            if not plugin.definition.get('handlers'):
                continue
            for handler in plugin.definition.get('handlers'):
                # some plugins want to listen to all incoming data
                if handler == 'ALL':
                    send_to_plugin = True
                # also if there is no header, we will send it to any plugin that wants all received data
                # this might be if the plugin us not using hamChat's standard data format, like
                # if someone wrote an IRC plugin where the header was not desired to be encoded in another user's reply.
                if not header:
                    break
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
                try:
                    plugin.on_payload_recieved({'header': header, 'payload': payload})
                except Exception as e:
                    print(f"Plugin {plugin.definition.get('name')} failed to handle payload: '{header + payload}' with error {e}")
                    self.host_interface.display_warning_box(f"Plugin {plugin.definition.get('name')} failed to handle a payload. Check the console for more information.")
    
    def on_command_received(self, command: str):
        for plugin in self.plugins:
            try:
                plugin.on_command_received(command)
            except Exception as e:
                self.__plugin_exception('on_command_received', plugin, e, f"Command: {command}")

    def append_bytes_to_buffer(self, data: bytes):
        # only send to the current selected transport by the host application
        for plugin in self.plugins:
            if plugin.definition.get('transport') == self.host_interface.settings.get('transport'):
                try:
                    plugin.append_bytes_to_buffer(data)
                except Exception as e:
                    self.__plugin_exception('append_bytes_to_buffer', plugin, e, f"Data: {data}")

    def on_transmit_buffer(self):
        for plugin in self.plugins:
            try:
                plugin.on_transmit_buffer()
            except Exception as e:
                self.__plugin_exception('on_transmit_buffer', plugin, e)
    
    def on_clear_buffer(self):
        for plugin in self.plugins:
            try:
                plugin.on_clear_buffer()
            except Exception as e:
                self.__plugin_exception('on_clear_buffer', plugin, e)
    
    def on_ui_transport_status_frame(self, tkParent):
        for plugin in self.plugins:
            try:
                plugin.on_ui_transport_status_frame(tkParent)
            except Exception as e:
                self.__plugin_exception('on_ui_transport_status_frame', plugin, e)

    def on_key_transmitter(self):
        for plugin in self.plugins:
            try:
                plugin.on_key_transmitter()
            except Exception as e:
                self.__plugin_exception('on_key_transmitter', plugin, e)
    
    def on_unkey_transmitter(self):
        for plugin in self.plugins:
            try:
                plugin.on_unkey_transmitter()
            except Exception as e:
                self.__plugin_exception('on_unkey_transmitter', plugin, e)

    def create_plugin_frames(self, tkParent):
        for plugin in self.plugins:
            try:
                plugin.create_plugin_frame(tkParent)
            except Exception as e:
                self.__plugin_exception('create_plugin_frame', plugin, e)
    
    def on_get_data(self) -> bytes:
        for plugin in self.plugins:
            try:
                plugin.on_get_data()
            except Exception as e:
                self.__plugin_exception('on_get_data', plugin, e)
    
    def on_settings_update(self):
        for plugin in self.plugins:
            try:
                plugin.on_settings_update()
            except Exception as e:
                self.__plugin_exception('on_settings_update', plugin, e)
    
    def on_shutdown(self):
        for plugin in self.plugins:
            try:
                plugin.on_shutdown()
            except Exception as e:
                self.__plugin_exception('on_shutdown', plugin, e)

    def IPC(self, target_plugin: str, from_plugin: str, command: str, data: bytes = None):
        for plugin in self.plugins:
            if plugin.definition.get('name') == target_plugin:
                try:
                    plugin.IPC(target_plugin=target_plugin, from_plugin=from_plugin, command=command, data=data)
                except Exception as e:
                    self.__plugin_exception('IPC', plugin, e, f"Command: {command} Data: {data}")
