###############################################################################
# MicroPython LoRa transmitter using loraE22
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
# 20211018 created
#
######################################################################

from loraE22 import ebyteE22
import machine
from machine import Pin
import utime
import ubinascii

me   = 0
peer = 1
addr = [0x0000, 0x0001]
chan = [0x00, 0x00]

M0pin = 25
M1pin = 26
AUXpin = 14

e22 = ebyteE22(M0pin, M1pin, AUXpin, Port='U2', Address=addr[me], Channel=chan[me], debug=False)

unique_id = ubinascii.hexlify(machine.unique_id()).decode("ascii")

# enable appending of RSSI to RX message
e22.config['rssi'] = 1

e22.start()

msg_no = 0
while True:
    message = "ESP32 ID: {} / MsgNo: {}".format(unique_id, msg_no)
    tx_msg = { 'msg': message }
    print('Node %d TX: address %d - channel %d - message %s'%(me, addr[peer], chan[peer], tx_msg))
    e22.sendMessage(addr[peer], chan[peer], tx_msg, useChecksum=True)
    msg_no += 1
    utime.sleep_ms(2000)

e22.stop()
