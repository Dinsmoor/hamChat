## ARDOPCF FEC CHAT (soon to be called hamChat once the plugin system is perfected)

*Consider this software unstable and subject to extreme changes*

This program by itself provides keyboard-to-keyboard text chat using the ARDOPCF sound modem over a traciever controlled by rigctld. Its power is that almost any functionality can be added via plugins.

There is an included example plugin that provides very basic file transfer, with no guarantee of completeness or correctness.

## Usage

Have the following software running
- ardopcf
- rigctld (if you use vox just don't specify a rig and it will be a dummy port)

then run hamchat with `python3 main.py`

## Plugins

Plugins are python files that inherit the ARDOPCFPlugin class, and are called by PluginManager when an event fires,
such as whenever the UI state is updated or if the TNC recieves a data packet that the plugin handles
(specified in self.definition). 

Plugins can add new windows or widgets, directly issue commands to the TNC, or do pretty much anything.

# Plugin Rules
1. Plugins must be in the ARDOPCF_Plugins folder
2. Plugins must begin with the filename ARDOPCFPlugin
3. Plugins must minimally have an `def __init__(self, host_interface):` and specify info and their definition as object variables.
   - Plugins can access all parts of the UI and TNC via the host_interface object.
   - See ARDOPCFPluginFileTransfer.py or ARDOPCPluginCore.py or ARDOPCPlugin.py for examples
1. See ARDOPCFPlugin.py for what hooks are implemented.
2. To recieve and process incoming data, at least one protocol handler must be specified in self.definition.

# Ideas for Plugins
- Over-the-air Plugin sharing
  - Plugin mismatch can be resolved via file transfer
- Data ACK
  - Non-connected mode (FEC) delivery confirmation
- Modulation mode testing
  - Measure effective throughtput for different data modes.
- TNC status window
  - Separate section of UI to have the current
- Automatic Link Establishment
  - Use rigctld to hop around frequencies waiting to be 'called'
- ARQ mode
  - More robust for 1-on-1
- Rig Control
  - Currentl rigctld is accessed as part of the main program, but this should be moved to a plugin.
- Data Mode Negotiation
  - If you have a large file, auto negotiate the fastest data rate avaliable for the channel.
- Data Relay Request
  - A -> B went OK, but C wanted it too. C can request B to give it to them.
- GPSD Squaking
  - Send an APRS-compatible message (or whatever message we might want)
- XASTIR KISS TNC emulator
  - Interface with existing APRS software through ARDOP
- Notification System
  - Ding on message reciept, send you an email or text message, or connect to a custom phone app
- BBS Server
  - If clients connect to you, you can post and respond to messages.

# Non-plugin ideas that would significantly change how this program and plugins work
- Other Transports besides ARDOP
  - Would require a bit of a rewrite of the frontend, but you could have a TCP/VARA/Packet transports while still getting to use the plugin system. Interfacing with ARDOP would become its own plugin for example, avalibale
  transports would be avaliable from a drop-down. Each Transport would have its own configuration menu.
- Web Interface
  - Would require refactoring for headless installation (raspberry pi)
  but may be hard for plugins to deal with. Maybe an abstraction layer
  takes the ui elements avaliable in tkinter or Django (or something)
  and creates each, however this would be way way too complicated.
  This will probably never happen.