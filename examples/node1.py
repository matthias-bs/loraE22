###############################################################################
# MicroPython bi-directional point-to-point LoRa transmission using loraE22
# (Tested with ESP32-WROOM-32 modules) 
#
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

# enable appending of RSSI to RX message
e22.config['rssi'] = 1

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
        print('-> LED: %s, RSSI=%d dBm'%(rx_msg['led'], rx_msg['rssi']))
        rx_val = 0 if rx_msg['led'] == '0' else 1 
        led.value(rx_val)
    utime.sleep_ms(2000)

e22.stop()
