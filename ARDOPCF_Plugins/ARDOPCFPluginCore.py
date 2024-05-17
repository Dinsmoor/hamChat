# inherits from ARDOPCFPlugin
from ..ARDOPCFPlugin import ARDOPCFPlugin
# import to assist with type hinting
from ..main import ARDOPCFGUI

class ARDOPCFPluginCore(ARDOPCFPlugin):
    def __init__(self, host_interface=ARDOPCFGUI):
        super().__init__(host_interface)

        self.info = """
        This plugin exists to provide versioning information to other plugins.
        When a plugin depends on this plugin's version, it depends on the version of the ARDOP Chat application.
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
        