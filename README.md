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

## NOTE

1. The E22 and E32 are different in many details - 
   - commands
   - register layout
   - mode control
   - AUX signal timing (in Configuration mode, AUX cannot be used to detect completion of command/response sequence)
2. The E22 or E32 modules do not seem to be suitable for LoRaWAN communication
   (e.g. The Things Network)

## Test code
**Note:** The E22 test code differs from the E32 test code in terms of used UART and AUX pin! 

Transmission mode | TX (Addr - Ch) | RX (Addr - Ch) | Transmitter Code | Receiver Code
:---: | :------: | :------: | :----: | :----:
|transparent|0x0001 - 0x02|0x0001 - 0x02|[testSendE32_Transparent.py](examples/testSendE32_Transparent.py)|[testRecvE32_Transparent.py](examples/testRecvE32_Transparent.py)
|fixed P2P|0x0001 - 0x02|0x0003 - 0x04|[testSendE32_P2P.py](examples/testSendE32_P2P.py)|[testRecvE32_P2P.py](examples/testRecvE32_P2P.py)
|fixed broadcast|0x0001 - 0x02|0x0003 - 0x04|[testSendE32_Broadcast.py](examples/testSendE32_Broadcast.py)|[testRecvE32_Broadcast.py](examples/testRecvE32_Broadcast.py)
|fixed monitor|0x0001 - 0x02|0xFFFF - 0x04|[testSendE32_Monitor.py](examples/testSendE32_Monitor.py)|[testRecvE32_Monitor.py](examples/testRecvE32_Monitor.py)
