# hamChat

*Consider this software unstable and subject to extreme changes*

This program is a desktop application that allows amatuer radio operators to do almost whatever they want
within the context of text or binary data transfer, via a plugin system.

![image](https://github.com/Dinsmoor/hamChat/assets/3772345/9a220a17-47ce-4590-9cd5-8810ec910520)


Currently, the following features are implemented:
- Keyboard-to-Keyboard text chat (integral to the main program)
- ARDOP FEC mode transport
- hamlib rig control (mainly used for keying)
- Simple File Transfer
- autoACK message length acknowledgment

# Usage

Have the following software running
- ardopcf (if using the ardop plugin)
- rigctld (if using the hamlib plugin)

Run hamchat with `python3 main.py`


## Plugins

**DO NOT WRITE PLUGINS FOR THIS YET!**

Plugins are python files that inherit the hamChatPlugin class, and are located in the plugins folder.

Events will be called by the hamChat, and if a plugin has a hook for it, it will be called.

Plugins can add new windows or widgets, directly issue commands to the TNC, or do pretty much anything.

The reason why you should not write plugins yet, is because I haven't decided the amount of control I will
let them have, and there may be an issue with resolving conflict, if, for example, more than one plugin trys
to mess with the same UI element or the chat window. Certain things are also currently unavaliable in a sane way.

Most of all, method names are probably going to change a lot, because I don't like their names, and I want them to make
sense and be easy for the plugin authors to understand exactly what they do.

## Plugin Rules
1. Plugins files (python) go in the `plugins` folder (plugin authors should write their settings here too)
2. All classes in that folder that inherit from `hamChatPlugin` will be loaded.
3. Plugin class initialization must accept one argument, which is the GUI instance object.
   - See plugin folder for examples

## Ideas for Plugins
- Over-the-air Plugin sharing
  - Plugin mismatch can be resolved via file transfer
- Modulation mode testing
  - Measure effective throughtput for different data modes.
- Automatic Link Establishment
  - Use rigctld to hop around frequencies waiting to be 'called'
- ARQ mode support (for ardop, at least)
  - More robust for 1-on-1 with transport-level link speed negotiation.
  - Should be better for file transfer > 500 bytes than Simple File Transfer
- Advanced Rig Control
  - Frequency and mode changing
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
- Callsign resolving
  - Fetch from QRZ or something
- Cross-transport forwarding
  - If someone is on TCP, you can relay their messaged through ardop or something.
- Message translation
  - If someone is chatting in another language, automatically translate to and from their language.

## Writing Plugins

0. Be WARNED that the plugin interface may change in the future. If this does, the 'Core' plugin version will increment.
1. Copy hamChatPlugin.py to your new plugin file name, into the `plugins` folder
2. Rename the hamChatPlugin to whatever you like, and inherit from `hamChatPlugin`.
3. Write your `self.description`. Be sure to declare any new handlers if you expect to send or receive messages over a transport.
4. Read the entirity of the comments and examples in `__init__`, they tell you how best to interface with the main program.
5. Read all the default methods and their descriptions to figure out when you want your code to run. Take note:
   1. Except for `on_transport_state_update()` and `on_get_data()` - all other methods run on the same thread as the UI.
   2. Don't write anything in these methods that is blocking/dependant on another plugin to perform a task.
   3. It is better for you to start your own worker thread to manage all of the internal state requirements.
   4. Code written in these methods should have robust error handling. If they fail, they will crash the main thread. I do not want to get bug reports on this repository for custom plugin issues.
6. Keep It Simple, Stupid!
   1. Plugins can communicate with one another. Each plugin should add ONE function/feature. There is no need to pack 10 features into one plugin. This makes them harder to interface with.
7. If another plugin doesn't provide a hook that you need, feel free to fork it and submit a pull request.
   1. When testing plugin revisions on-air, be sure to change the version number if the changes you make are incompatible with the source version.
8. TEST THESE ON AIR WITH MULTPLE STATIONS BEFORE COMMITTING! Avoid WOMM (Works On My Machine) syndrome as much as possible.
9. Provide feedback on how development went. For me, because I wrote the whole ting, it's easy to remember how to work around issues. If there is a problem where doing something is harder than it should be, and you've reviewed all the example plugins, please send an email or open an issue.

## Known Bugs
1. ARDOPCF will sometimes drop incoming messages, even if properly decoded, with a message like: `[ARDOPprotocol.ProcessRcvdFECDataFrame] Same Frame ID: 4FSK.500.100.E and matching data, not passed to Host` even if the frame sent is NOT a FEC Repeat. That's why autoACK is important until that bug is fixed.
2. If there is unprocessed data in the incoming data buffer, especially if it's not a complete hamChat packet, it will be lost/ignored.

## Troubleshooting
1. Sometimes you need to send an empty chat packet/recieve at least one packet for ardop to 'get with the program' and start giving you good data. Once I figure out why this is happening, I'll try to fix it.
2. If your data never sends, make sure you are running ardop with the proper arguments. I often accidentally leave out the second audio source identifier.
3. Some standard plugins like Simple File Transfer may have bugs. I don't rigorously test everything every commit yet, because this program is unstable.
