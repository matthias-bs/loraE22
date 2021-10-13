# Simple test program for loraE22 receiver
# based on https://github.com/effevee/loraE32

###########################################
# receiving fixed broadcast
###########################################
# transmitter - address 0001 - channel 02
# message     - address FFFF - channel 04
# receiver(s) - address 0003 - channel 04
###########################################

from loraE22 import ebyteE22
import utime

M0pin = 25
M1pin = 26
AUXpin = 14

e22 = ebyteE22(M0pin, M1pin, AUXpin, Port='U2', Address=0x0003, Channel=0x04, debug=False)

e22.start()

from_address = 0xFFFF
from_channel = 0x04

while True:
    print('Receiving fixed broadcast : address %d - channel %d'%(from_address, from_channel), end='')
    message = e22.recvMessage(from_address, from_channel, useChecksum=True)
    print(' - message %s'%(message))
    utime.sleep_ms(2000)

e22.stop()
