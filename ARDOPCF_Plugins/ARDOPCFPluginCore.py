# inherits from ARDOPCFPlugin
from ARDOPCFPlugin import ARDOPCFPlugin

class ARDOPCFPluginCore(ARDOPCFPlugin):
    def __init__(self, host_interface: object):
        super().__init__(host_interface)

        self.info = f"""
        This plugin exists to provide main application versioning information to
        other plugins.
        """
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Core Plugin',
            'version': host_interface.version,
            'description': self.info,
            'protocol_identifier': '',
            'handlers': [],
            'protocol_fields': [],
            'provides': self.__class__.__name__,
            'depends_on': [],
        }
        