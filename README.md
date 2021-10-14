# loraE22
A MicroPython class for the Ebyte E22 Series LoRa modules

The supported EBYTE E22 modules are based on SEMTECH SX1262/SX1286 chipsets and are available for the 
400 MHz (410.125...493.125) and
900 MHz (850.125...930.125) frequency ranges and provide 20 dBm max. TX power.  

A simple UART interface is used to control the device.

**EBYTE Datasheets:**<br>
[E22-900T22D](https://www.ebyte.com/en/product-view-news.html?id=1117)<br>
[E22-400T22D](https://www.ebyte.com/en/product-view-news.html?id=922)


The loraE22 class is based on the loraE22 class by effevee:
https://github.com/effevee/loraE32

**Connect proper antenna before transmitting!**

## NOTE

1. The E22 and E32 are different in many details - 
   - commands
   - register layout
   - mode control
   - AUX signal timing (in Configuration mode, AUX cannot be used to detect completion of command/response sequence)
2. The E22 or E32 modules do not seem to be suitable for LoRaWAN communication
   (e.g. The Things Network)

## Test code
**Notes:** The loraE22 test code differs from the E32 test code in terms of used UART and AUX pin! Furthermore, loraE22 uses 'normal mode', while loraE32 uses 'wakeup mode' in *sendMessage()*. 

Transmission mode | TX (Addr - Ch) | RX (Addr - Ch) | MSG (Addr - Ch) | Transmitter Code | Receiver Code
:---: | :------: | :------: | :------: | :----: | :----:
|transparent|0x0001 - 0x02|0x0001 - 0x02|0x0001 - 0x02|[testSendE22_Transparent.py](examples/testSendE22_Transparent.py)|[testRecvE22_Transparent.py](examples/testRecvE22_Transparent.py)
|fixed P2P|0x0001 - 0x02|0x0003 - 0x04|0x0003 - 0x04|[testSendE22_P2P.py](examples/testSendE22_P2P.py)|[testRecvE22_P2P.py](examples/testRecvE22_P2P.py)
|fixed broadcast|0x0001 - 0x02|0x0003 - 0x04|0xFFFF - 0x04|[testSendE22_Broadcast.py](examples/testSendE22_Broadcast.py)|[testRecvE22_Broadcast.py](examples/testRecvE22_Broadcast.py)
|fixed monitor|0x0001 - 0x02|0xFFFF - 0x04|0x0003 - 0x04|[testSendE22_Monitor.py](examples/testSendE22_Monitor.py)|[testRecvE22_Monitor.py](examples/testRecvE22_Monitor.py)

## Example: Bi-directional transmission between two nodes

Each node sends a message at a fixed interval containing an LED control 
value according to the state of a push button.

Afterwards it checks for received messages. If a message with LED control
value is available, the LED is switched accordingly.

The transmission mode (address/channel config) for the local node and the
peer node can be set as desired in the arrays *addr* and *chan*.

The code of [node0.py](examples/node0.py) and [node1.py](examples/node1.py) is identical except for the settings of
the variables *me* and *peer*.

Node0 | Node1
:---: | :---: 
[node0.py](examples/node0.py)|[node1.py](examples/node1.py)
