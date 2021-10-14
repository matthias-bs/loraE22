###############################################################################
# MicroPython bi-directional point-to-point LoRa transmission using loraE22
# (Tested with ESP32-WROOM-32 modules) 
#
# Each node sends a message at a fixed interval containing an LED control 
# value according to the state of a push button.
# Afterwards it checks for received messages. If a message with LED control
# value is available, the LED is switched accordingly.
#
# The transmission mode (address/channel config) for the local node and the
# peer node can be set as desired in the arrays <addr> and <chan>.
#
# The code of node0.py and node1.py is identical except for the settings of
# the variables <me> and <peer>.
#
# Copyright (C) 10/2021 Matthias Prinke
# 
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# created: 10/2021
#
# History:
#
# 20211014 initial release
#
######################################################################

from loraE22 import ebyteE22
from machine import Pin
import utime

me   = 1
peer = 0
addr = [0x0000, 0x0001]
chan = [0x00, 0x00]

M0pin = 25
M1pin = 26
AUXpin = 14
LEDpin = 2
KEYpin = 0

led = Pin(LEDpin, Pin.OUT, value=0)
key = Pin(KEYpin, Pin.IN)

e22 = ebyteE22(M0pin, M1pin, AUXpin, Port='U2', Address=addr[me], Channel=chan[me], debug=False)

e22.start()

while True:
    tx_val = '0' if key.value() == 1 else '1'
    tx_msg = { 'led': tx_val }
    print('Node %d TX: address %d - channel %d - message %s'%(me, addr[peer], chan[peer], tx_msg))
    e22.sendMessage(addr[peer], chan[peer], tx_msg, useChecksum=True)
    rx_msg = e22.recvMessage(addr[peer], chan[peer], useChecksum=True)
    #print(rx_msg)
    if ('led' in rx_msg):
        print('Node %d RX: address %d - channel %d - message %s'%(me, addr[peer], chan[peer], rx_msg))
        rx_val = 0 if rx_msg['led'] == '0' else 1 
        led.value(rx_val)
    utime.sleep_ms(2000)

e22.stop()
