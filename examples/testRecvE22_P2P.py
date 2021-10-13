# Simple test program for loraE22 receiver
# based on https://github.com/effevee/loraE32

###########################################
# receiving fixed point to point
###########################################
# transmitter - address 0001 - channel 02
# message     - address 0003 - channel 04
# receiver    - address 0003 - channel 04
###########################################

from loraE22 import ebyteE22
import utime

M0pin = 25
M1pin = 26
AUXpin = 14

e22 = ebyteE22(M0pin, M1pin, AUXpin, Port='U2', Address=0x0003, Channel=0x04, debug=True)

e22.start()

e22.getConfig()

from_address = 0x0001
from_channel = 0x02

while True:
    print('Receiving fixed P2P: address %d - channel %d'%(from_address, from_channel), end='')
    message = e22.recvMessage(from_address, from_channel, useChecksum=True)
    print(' - message %s'%(message))
    utime.sleep_ms(2000)

e22.stop()
