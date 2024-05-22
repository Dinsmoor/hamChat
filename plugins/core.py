# inherits from Plugin
from hamChatPlugin import hamChatPlugin

"""
Standard hamChat header format:
0       1    2      3        4          5         6 (-1)
N0CALL:chat:0.1:RECIPIENTS:BEGIN:Hello, YOURCALL!:END:
"""

class Core(hamChatPlugin):
    def __init__(self, host_interface: object):
        super().__init__(host_interface)

        self.info = f"""
        This plugin exists to provide main application versioning information to
        other plugins.
        """
        self.definition = {
            'author': 'Tyler Dinsmoor/K7OTR',
            'name': 'Core',
            'version': host_interface.version,
            'description': self.info,
            'transport': '',
            'handlers': [],
            'protocol_fields': [],
            'depends_on': [],
        }
        