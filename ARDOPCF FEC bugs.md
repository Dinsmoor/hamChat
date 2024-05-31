ardopcf Version 1.0.4.1.1+develop
# FEC Mode Bugs


## Frame order host passing rejection bug

3 FEC frames are sent from station A at 4PSK.500.100.E/O

A send: Even Frame (decoded PASS, passed to host)
A send: Odd Frame (not recieved (off frequency, or transmitter did not key it) )
A send: Even Frame (decoded PASS, NOT passed to host)

Upon recieving an E frame, if the next O frame is missed (not decoded at all),
and the next E frame is recieved, ARDOP will discard the second E frame,
even if the payload is different.


## FEC Initial decode rejection bug
When ardopcf is first initialized for FEC mode, the first frame sent/recieved
in FEC mode is ignored by the receiving station.
(Needs additional testing)


## FEC Data buffer FEC declaration repeat bug (FECFEC)
If the data buffer is loaded with any message and sent, the data buffer
provided to the receiving station's host will always have a double FEC
declaration. If a message is split across multiple frames, only the first
frame in that series will have the double FEC. Not sure if this is
intentional behavior or not, but either way, it is undocumented as far as
I could tell in the source code.

<2 big endian length bytes><mode declaration><data>
	sent		received
1. x00x05FECHello  | x00x05FECFECHello
2. x00x06FECHappy! | x00x06FECFECHappy!


## FEC Data buffer repeat bug
In FEC mode, ARDOPCF will sometimes send data from other frames when a new frame
is recieved with different data.
(the FECFEC when reading the data buffer on the recieve side is a separate bug)

Sending station sends 3 frames with different data content, but same data length.
Format is data sent to sending station buffer | data read from receiving station buffer
<2 big endian length bytes><mode declaration><data>
	sent		received
1. x00x05FECHello | x00x05FECFECHello
2. x00x05FECHappy | x00x05FECFECHappy
3. x00x05FECNope! | x00x05FECFECHappy

In the debug logs, frames 1, 2, 3 all look fine and normal. 
