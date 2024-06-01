# hamChat

*Consider this software unstable and subject to extreme changes*

This program is a desktop application that allows amatuer radio operators to do almost whatever they want
within the context of text or binary data transfer, via a plugin system. Usually, this means using an
audio baseband over a radio link with a modem. Such as:

``` 
hamChat                        Radio
---rig control ------>PTT/CAT |     |\___>Radio link to another station
---sound modem ------>AUDIO   |     |/   >Also running hamChat
```

It is written in python3.6+, and uses no special libraries. It is also not very good (yet.)

![image](https://github.com/Dinsmoor/hamChat/assets/3772345/9a220a17-47ce-4590-9cd5-8810ec910520)


Currently, the following features are implemented:
- Keyboard-to-Keyboard text chat
- ARDOP FEC mode transport
- hamlib rig control (PTT and frequency/mode display)
- Simple File Transfer
- autoACK message acknowledgment
- Recently heard stations list

# Usage

If you have already run amatuer software before, like direwolf, then runing this program is relatively straight forward. 

To use this program, you need:
 1. Graphical Environment (Linux Recommended)
 2. Python 3.6+ interpreter -> https://www.python.org/downloads/ (or your system repositories)
 3. The ARDOPCF modem -> https://github.com/pflarue/ardop/releases/
 4. A way to connect to a radio (one of the following)
    1. Signalink USB -> https://tigertronics.com/slusbmain.htm
       1. Uses VOX to trigger the PTT line, but may have issues with timing/delay.
       2. May also trigger PTT with CAT/RTS/DTR, this is preferred but dependant on radio.
    2. Digirig Mobile -> https://digirig.net/
       1. Uses CAT or Serial RTS for PTT. Requires Hamlib.
       2. Works with BaoFeng
    3. Built-in USB interface (such as Yaesu FT-991A)
       1. Requires Hamlib


To run this program:

- start ardopcf
  - https://github.com/pflarue/ardop/releases/
  - run like `./ardopcf 8515 plughw:1,0 plughw:1,0`
  - plughw:1,0 is whatever audio interface your radio is hooked up to. Yes, you must repeat it twice. 8515 is the TCP port that hamChat will default to.
  - If you get audio errors, like "cannot open playback audio device" - check your device identifier. You may need to reboot or reload alsa/pulseaudio, or just wait a few seconds for any other application to 'let it go'. Or you invoked ardopcf incorrectly.


- start rigctld (this is part of hamlib)
  - On Ubuntu, install the package `libhamlib-utils`
  - Otherwise, compile from https://github.com/Hamlib/Hamlib
  - Check if you have a supported radio with `rigctl -l`
  - If supported, run like `rigctld -m your_radio_id -r /dev/ttyUSB0`
    - where your_radio_id is the number you got from rigctl -l, and /dev/ttyUSB0 is whatever serial port you have your radio connected to
  - If NOT supported, try a similar model. If that doesn't work, and you are using something like a digirig for PTT:
    - Try: `rigctld --ptt-file=/dev/ttyUSB0 --ptt-type=RTS`
  - If you get a "Permission Denied" error - you either need to get ownership of the virtual serial port or add yourself to the dialout group. Don't run rigctld as sudo.
    - `sudo chown $USER:$USER /dev/ttyUSB0` and/or
    - `sudo adduser $USER dialout` (then log out and back in)

- hamChat
  - Download or clone this repository
  - Run hamchat with `python3 ./main.py`

## Known Bugs
0. See `ARDOPCF FEC bugs.md`
1. If an internal thread crashes, it's not always made apparent to the user, and certain features will stop working. The program may need to be restarted if this happens.
2. If the main thread crashes, the program will not exit cleanly. Multiple CTRL+C in the terminal window may be needed.

## Troubleshooting
1. When using ARDOPCF, sometimes you need to send one packet/recieve at least one packet for ardopcf to start giving you good data.
2. If your data never sends, make sure you are running ardopcf with the proper arguments.


# For Developers

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

## Writing Plugins

STOP! - It's not ready. If you decide to anyway:

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

## Ideas for Plugins
- Automatic Link Establishment
  - Use rigctld to hop around frequencies waiting to be 'called'
- Advanced Rig Control (virtual VFO/frequency favorites)
- Data Mode Negotiation
  - If you have a large file, auto negotiate the fastest data rate avaliable for the channel.
  - (may be rolled in with ARQ modes)
- Data Relay Request
  - A -> B went OK, but C wanted it too. C can request B to give it to them.
- gpsd Squaking
  - Send an APRS-compatible message (or whatever message we might want)
- Notification System
  - Ding on message reciept, send you an email or text message, or connect to a custom phone app
- BBS Server
  - If clients connect to you, you can post and respond to messages in a local database.
- Callsign resolving
  - Fetch from QRZ or something
- Cross-transport forwarding
  - If someone is on TCP, you can relay their messaged through ardop or something.
- Message translation
  - If someone is chatting in another language, automatically translate to and from their language.
