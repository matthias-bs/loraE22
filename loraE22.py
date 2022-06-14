###############################################################################
# MicroPython class for EBYTE E22 Series LoRa modules
# Copyright (C) 09/2021 Matthias Prinke
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
# The supported EBYTE E22 modules are based on SEMTECH SX1262/SX1286
# chipsets and are available for the 
# 400 MHz (410.125~493.125)
# and
# 900 MHz (850.125~930.125)
# frequency ranges and provide 22 dBm max. TX power.
#
# A simple UART interface is used to control the device.
#
# The loraE22 class is based on the loraE22 class by effevee:
# https://github.com/effevee/loraE32
#
# created: 09/2021
#
# History:
#
# 20210913 initial release (not tested thoroughly)
# 20211013 fixed configuration timing and setting of configuration in start()
# 20211014 added optional output of RSSI
#
# NOTE:
# 1. The E22 and E32 are different in many details - 
#   - commands
#   - register layout
#   - mode control
#   - AUX signal timing -
#     in Configuration mode, AUX cannot be used to
#     detect completion of command/response sequence
# 2. The E22 or E32 do not seem to be suitable for LoRaWAN communication
#    (e.g. The Things Network)
#
#
# Pin layout E22-868T20D
# ======================
# +---------------------------------------------+
# | 0 - M0  (set mode)        [*]               |
# | 0 - M1  (set mode)        [*]               |
# | 0 - RXD (TTL UART input)  [*]               |
# | 0 - TXD (TTL UART output) [*]               |
# | 0 - AUX (device status)   [*]               |
# | 0 - VCC (3.3-5.2V)                          +---+
# | 0 - GND (GND)                                SMA| Antenna
# +-------------------------------------------------+
#     [*] ALL COMMUNICATION PINS ARE 3.3V !!!
#
#
# Transmission modes :
# ==================
#   - Transparent : all modules have the same address and channel and
#        can send/receive messages to/from each other. No address and
#        channel is included in the message.
#
#   - Fixed : all modules can have different addresses and channels.
#        The transmission messages are prefixed with the destination address
#        and channel information. If these differ from the settings of the
#        transmitter, then the configuration of the module will be changed
#        before the transmission. After the transmission is complete,
#        the transmitter will revert to its prior configuration.
#
#        1. Fixed P2P : The transmitted message has the address and channel
#           information of the receiver. Only this module will receive the message.
#           This is a point to point transmission between 2 modules.
#
#        2. Fixed Broadcast : The transmitted message has address FFFF and a
#           channel. All modules with any address and the same channel of
#           the message will receive it.
#             
#        3. Fixed Monitor : The receiver has adress FFFF and a channel.
#           It will receive messages from all modules with any address and
#           the same channel as the receiver.
#
#
# Operating modes :
# ===============
#   - 0=Normal mode (M0=0,M1=0):
#
#     UART and wireless channel are open, transparent transmission is on.
#
#
#   - 1=WOR mode (M0=1,M1=0): 
#
#     Can be defined as WOR transmitter and WOR receiver
#     (wake-up on radio).
#
#
#   - 2=Configuration mode (M0=0,M1=1):
#
#     Users can access the register through the serial port to control
#     the working state of the module.
#
#
#   - 3=Deep sleep mode (M0=1,M1=1):
#
#     Sleep mode.
#
######################################################################

from machine import Pin, UART
import utime
import ujson
import binascii


class ebyteE22:
    ''' class to interface an ESP32 via serial commands to the EBYTE E32 Series LoRa modules '''
    
    # UART ports
    PORT = { 'U0':0, 'U1':1, 'U2':2 , 'U3':3}
    # UART parity strings
    PARSTR = { '8N1':'00', '8O1':'01', '8E1':'10' }
    PARINV = { v:k for k, v in PARSTR.items() }
    # UART parity bits
    PARBIT = { 'N':None, 'E':0, 'O':1 }
    # UART baudrate
    BAUDRATE = { 1200:'000', 2400:'001', 4800:'010', 9600:'011',
                 19200:'100', 38400:'101', 57600:'110', 115200:'111' }
    BAUDRINV = { v:k for k, v in BAUDRATE.items() }
    # LoRa datarate
    DATARATE = { '0.3k':'000', '1.2k':'001', '2.4k':'010',
                 '4.8k':'011', '9.6k':'100', '19.2k':'101',
                 '38.4k':'110','62.5k':'111' }
    DATARINV = { v:k for k, v in DATARATE.items() }
    # Commands
    CMDS = { 'setConfigPwrDwnSave':0xC0,
             'getConfig':0xC1,
             'setConfigPwrDwnNoSave':0xC2,
             'getVersion':0xC3}
    # operation modes (set with M0 & M1)
    OPERMODE = { 'normal':'00', 'wakeup':'10', 'config':'01', 'sleep':'11' }
    # model frequency ranges (MHz)
    FREQ = { 170:[160, 170, 173], 400:[410, 470, 525], 433:[410, 433, 441],
             868:[862, 868, 893], 915:[900, 915, 931] }
    # version info frequency
    FREQV = { '0x32':433, '0x38':470, '0x45':868, '0x44':915, '0x46':170 }
    # model maximum transmission power
    #FIXME do we still need this? 
    MAXPOW = { 'T22':0, 'T17':1, 'T13':2, 'T10':3 }
    # RSSI enable
    RSSI = { 0:'disable', 1:'enable' }
    # transmission mode
    TRANSMODE = { 0:'transparent', 1:'fixed' }
    # repeater mode
    REPEATER = { 0:'disable', 1:'enable' }
    # LBT
    LBT = { 0:'disable', 1:'disabe' }
    
    # wireless wakeup times from sleep mode
    WUTIME = { 0b000:'500ms', 0b001:'1000ms', 0b010:'1500ms', 0b011:'2000ms',
               0b100:'2500ms', 0b101:'3000ms', 0b110:'3500ms', 0b111:'4000ms' }
    # transmission power T20/T27/T30 (dBm)
    TXPOWER = { 0b00:'22dBm', 0b01:'17dBm', 0b10:'13dBm', 0b11:'10dBm' }
    TXPWRINV= { '22dBm':0b00, '17dBm':0b01, '13dBm':0b10, '19dBm':0b11 }

    WORCTRL = { 0:'WOR receiver', 1:'WOR transmitter' }
    #  Sub packet setting
    SUBPINV = { '240B':'00', '128B':'01', '64B':'10', '32B':'11' }
    SUBPCKT = { 0b00:'240B', 0b01:'128B', 0b10:'64B', 0b11:'32B' }
    

    def __init__(self, PinM0, PinM1, PinAUX, Model='900T22D', Port='U1', Baudrate=9600, Parity='8N1', AirDataRate='2.4k', Address=0x0000, Netid=0x00, Channel=0x06, transmode=0, RSSI=0, TXpower='22dBm',debug=False):
        ''' constructor for ebyte E32 LoRa module '''
        # configuration in dictionary
        self.config = {}
        self.config['model'] = Model               # E22 model (default 868T20D)
        self.config['port'] = Port                 # UART channel on the ESP (default U1)
        self.config['baudrate'] = Baudrate         # UART baudrate (default 9600)
        self.config['parity'] = Parity             # UART Parity (default 8N1)
        self.config['datarate'] = AirDataRate      # wireless baudrate (default 2.4k)
        self.config['address'] = Address           # target address (default 0x0000)
        self.config['netid'] = Netid               # Network address
        self.config['channel'] = Channel           # target channel (0-31, default 0x06)
        self.config['amb_noise'] = 0
        self.config['rssi'] = RSSI
        self.config['transmode'] = transmode       # transmission mode (default 0 - tranparent)
        self.config['repeater'] = 0                # repeater mode (default 0 - disable repeater function)
        self.config['lbt'] = 0                     # LBT enable (default 0 - disable disabled)
        self.config['worctrl'] = 0                 # WOR transceiver control (default 0 - WOR receiver)
        self.config['wutime'] = 3                  # wakeup time from sleep mode (default 3 = 2000ms)
        self.config['txpower'] =self.TXPWRINV.get(TXpower,0) # transmission power (default 0 = 22dBm/158mW)
        # 
        self.PinM0 = PinM0                         # M0 pin number
        self.PinM1 = PinM1                         # M1 pin number
        self.PinAUX = PinAUX                       # AUX pin number
        self.M0 = None                             # instance for M0 Pin (set operation mode)
        self.M1 = None                             # instance for M1 Pin (set operation mode)
        self.AUX = None                            # instance for AUX Pin (device status : 0=busy - 1=idle)
        self.serdev = None                         # instance for UART
        self.minfreq = 850.125                     # Minimum frequency (frequency = (minfreq + CH) [MHz]
        self.debug = debug
        #
        self.calcFrequency()                       # calculate frequency

    def start(self):
        ''' Start the ebyte E32 LoRa module '''
        try:
            # check parameters
            if self.config['port'] not in ebyteE22.PORT:
                self.config['port'] = 'U1'
            if int(self.config['baudrate']) not in ebyteE22.BAUDRATE:    
                self.config['baudrate'] = 9600
            if self.config['parity'] not in ebyteE22.PARSTR:
                self.config['parity'] = '8N1'
            if self.config['datarate'] not in ebyteE22.DATARATE:
                self.config['datarate'] = '2.4k'
            if self.config['channel'] > 31:
                self.config['channel'] = 31
            # make UART instance
            par = ebyteE22.PARBIT.get(str(self.config['parity'])[1])
            self.serdev = UART(ebyteE22.PORT.get(self.config['port']),baudrate=self.config['baudrate'], bits=8, parity=None, stop=1)
            if self.debug:
                print(self.serdev)
            # make operation mode & device status instances
            self.M0 = Pin(self.PinM0, Pin.OUT)
            self.M1 = Pin(self.PinM1, Pin.OUT)
            self.AUX = Pin(self.PinAUX, Pin.IN, Pin.PULL_UP)
            if self.debug:
                print(self.M0, self.M1, self.AUX)
            self.setOperationMode('config')
            self.waitForDeviceIdle()
            # set config to the ebyte E22 LoRa module
            self.setConfig('setConfigPwrDwnSave')
            return "OK"
        
        except Exception as E:
            if self.debug:
                print("error on start UART", E)
            return "NOK"
        
  
    def sendMessage(self, to_address, to_channel, payload, useChecksum=False):
        ''' Send the payload to ebyte E22 LoRa modules in transparent or fixed mode. The payload is a data dictionary to
            accomodate key value pairs commonly used to store sensor data and is converted to a JSON string before sending.
            The payload can be appended with a 2's complement checksum to validate correct transmission.
            - transparent mode : all modules with the same address and channel of the transmitter will receive the payload
            - fixed mode : only the module with this address and channel will receive the payload;
                           if the address is 0xFFFF all modules with the same channel will receive the payload'''
        try:
            # type of transmission
            if (to_address == self.config['address']) and (to_channel == self.config['channel']):
                # transparent transmission mode
                # all modules with the same address and channel will receive the payload
                self.setTransmissionMode(0)
            else:
                # fixed transmission mode
                # only the module with the target address and channel will receive the payload
                self.setTransmissionMode(1)
            self.setOperationMode('normal')
            # check payload
            if type(payload) != dict:
                print('payload is not a dictionary')
                return 'NOK'
            # encode message
            msg = []
            if self.config['transmode'] == 1:     # only for fixed transmission mode
                msg.append(to_address//256)          # high address byte
                msg.append(to_address%256)           # low address byte
                msg.append(to_channel)               # channel
            js_payload = ujson.dumps(payload)     # convert payload to JSON string 
            for i in range(len(js_payload)):      # message
                msg.append(ord(js_payload[i]))    # ascii code of character
            if useChecksum:                       # attach 2's complement checksum
                msg.append(int(self.calcChecksum(js_payload), 16))
            # debug
            if self.debug:
                print(msg)
            # wait for idle module
            self.waitForDeviceIdle()
            # send the message
            self.serdev.write(bytes(msg))
            return "OK"
        
        except Exception as E:
            if self.debug:
                print('Error on sendMessage: ',E)
            return "NOK"
        
        
    def recvMessage(self, from_address, from_channel, useChecksum=False):
        ''' Receive payload messages from ebyte E32 LoRa modules in transparent or fixed mode. The payload is a JSON string
            of a data dictionary to accomodate key value pairs commonly used to store sensor data. If checksumming is used, the
            checksum of the received payload including the checksum byte should result in 0 for a correct transmission.
            - transparent mode : payload will be received if the module has the same address and channel of the transmitter
            - fixed mode : only payloads from transmitters with this address and channel will be received;
                           if the address is 0xFFFF, payloads from all transmitters with this channel will be received'''
        try:
            # type of transmission
            if (from_address == self.config['address']) and (from_channel == self.config['channel']):
                # transparent transmission mode
                # all modules with the same address and channel will receive the message
                self.setTransmissionMode(0)
            else:
                # fixed transmission mode
                # only the module with the target address and channel will receive the message
                self.setTransmissionMode(1)
            # put into normal mode
            self.setOperationMode('normal')
            # receive message
            js_payload = self.serdev.read()
            # debug
            if self.debug:
                print(js_payload)
            # did we receive anything ?
            if js_payload == None:
                # nothing
                return { 'msg':None, 'rssi':None }
            else :
                # decode message
                msg = ''
                if self.config['rssi']:
                    rssi = js_payload[-1]
                    # convert byte value to dBm
                    rssi = -(256 - rssi)
                    js_payload = js_payload[:-1]
                else:
                    rssi = None
                for i in range(len(js_payload)):
                    msg += chr(js_payload[i])
                # checksum check
                if useChecksum:
                    cs = int(self.calcChecksum(msg),16)
                    if cs != 0:
                        # corrupt
                        return { 'msg':'corrupt message, checksum ' + str(cs), 'rssi':rssi }
                    else:
                        # message ok, remove checksum
                        msg = msg[:-1]
                # Add rssi to JSON string
                if (rssi != None):
                    msg = msg[:-1] + ',"rssi":' + str(rssi) + '}'
                else:
                    # Note 'None' is not defined in JSON, use null instead
                    msg = msg[:-1] + ',"rssi": null }'
                # JSON to dictionary
                message = ujson.loads(msg)
                return message
        
        except Exception as E:
            if self.debug:
                print('Error on recvMessage: ',E)
            return "NOK"

    
    def calcChecksum(self, payload):
        ''' Calculates checksum for sending/receiving payloads. Sums the ASCII character values mod256 and returns
            the lower byte of the two's complement of that value in hex notation. '''
        return '%2X' % (-(sum(ord(c) for c in payload) % 256) & 0xFF)


    def stop(self):
        ''' Stop the ebyte E22 LoRa module '''
        try:
            if self.serdev != None:
                self.serdev.deinit()
                del self.serdev
            return "OK"
            
        except Exception as E:
            if self.debug:
                print("error on stop UART", E)
            return "NOK"
        
    
    def sendCommand(self, command, wireless_cmd=False):
        ''' Send a command to the ebyte E22 LoRa module.
            The module has to be in sleep mode '''
        try:
            # put into configuration mode
            self.setOperationMode('config')
            # send command
            HexCmd = ebyteE22.CMDS.get(command)
            # response time - time between complete transmission of command and reception of response
            # (FIXME how about wireless command?)
            # 200ms for 'setConfigPwrDwnSave' and 'setConfigPwrDwnNoSave'
            #  30ms for all other commands
            resp_time = 200 if HexCmd in [0xC0, 0xC2] else 30
            if HexCmd in [0xC0, 0xC2]:        # set config to device
                header = HexCmd
                HexCmd = self.encodeConfig()
                HexCmd[0] = header
            elif command == 'getConfig':
                HexCmd = [0xC1, 0x00, 0x07]
            elif command == 'getPID':
                HexCmd = [0xC1, 0x80, 0x07]
            if wireless_cmd:
                HexCmd = [0xCF, 0xCF] + HexCmd
            if self.debug:
                print(HexCmd)
            num = self.serdev.write(bytes(HexCmd))
            utime.sleep_ms(resp_time)
            # wait for result
            result = self.serdev.read()
            # debug
            if self.debug:
                print(result)
            return result
        
        except Exception as E:
            if self.debug:
                print('Error on sendCommand: ',E)
            return "NOK"

    
    def getConfig(self):
        ''' Get config parameters from the ebyte E22 LoRa module '''
        try:
            # send the command
            result = self.sendCommand('getConfig')
            # check result
            if len(result) != 10:
                return "NOK"
            # decode result
            self.decodeConfig(result)
            # show config
            self.showConfig()
            return "OK"

        except Exception as E:
            if self.debug:
                print('Error on getConfig: ',E)
            return "NOK"  
    

    def decodeConfig(self, message):
        ''' decode the config message from the ebyte E22 LoRa module to update the config dictionary '''
        # message byte 0 = command
        # message byte 1 = starting address
        # message byte 2 = response length
        header = int(message[0])
        # message byte 3 & 4 = address
        self.config['address'] = int(message[3])*256 + int(message[4])
        # message byte 5 = Net ID
        self.config['netid'] = int(message[5])
        # message byte 6 = REG0
        bits = '{0:08b}'.format(message[6])
        self.config['baudrate'] = ebyteE22.BAUDRINV.get(bits[0:3])
        self.config['parity'] = ebyteE22.PARINV.get(bits[4:6])
        self.config['datarate'] = ebyteE22.DATARINV.get(bits[5:])
        # message byte 7 = REG1
        bits = '{0:08b}'.format(message[7])
        self.config['subpckt'] = int('0b' + bits[0:1])
        self.config['amb_noise'] = int(bits[2])
        self.config['txpower'] = int('0b' + bits[6:])
        # message byte 8 = REG2 (channel)
        self.config['channel'] = int(message[8])
        # message byte 9 = REG3
        bits = '{0:08b}'.format(message[9])
        self.config['rssi'] = int(bits[0])
        self.config['transmode'] = int(bits[1])
        self.config['repeater'] = int(bits[2])
        self.config['lbt'] = int(bits[3])
        self.config['worctrl'] = int(bits[4])
        self.config['wutime'] = int('0b' + bits[5:])
        #print(self.config)
    
    def encodeConfig(self):
        ''' encode the config dictionary to create the config message of the ebyte E22 LoRa module '''
        # Initialize config message
        message = []
        # message byte 0 = header
        message.append(0xC0)
        # message byte 1 = starting address (register)
        message.append(0x00)
        # message byte 2 = length (of parameter sequence)
        message.append(0x07)
        # message byte 3 = ADDH (high address)
        message.append(self.config['address']//256)
        # message byte 4 = ADDL (low address)
        message.append(self.config['address']%256)
        # message byte 5 = NETID
        message.append(self.config['netid'])
        # message byte 6 = REG0 (serial baudrate, serial parity, air datarate)
        bits = '0b'
        bits += ebyteE22.BAUDRATE.get(self.config['baudrate'])
        bits += ebyteE22.PARSTR.get(self.config['parity'])
        bits += ebyteE22.DATARATE.get(self.config['datarate'])
        #print("REG0:", bits)
        message.append(int(bits))
        # message byte 7 = REG1 (Sub packet setting, Ambient noise enable, Transmitting power)
        bits = '0b'
        # Bits 7:6 - Sub packet setting
        bits += ebyteE22.SUBPINV.get('240B')
        # Bit 5 - RSSI Ambient Noise Enable
        bits += str(self.config['amb_noise'])
        # Bits 4:2 - reserved
        bits += '000'
        # Bits 1:0 - Transmitting power
        bits += '{0:02b}'.format(self.config['txpower'])
        #print("REG1:", bits)
        message.append(int(bits))
        # message byte 8 = REG2 (channel control)
        message.append(self.config['channel'])
        # message byte 9 = REG3 (rssi, transmode, enable_repeater, enable_lbt, wor_control, wor_cycle)
        bits = '0b'
        # Bit 7 - Enable RSSI
        bits += str(self.config['rssi'])
        # Bit 6 - Transmission mode 
        bits += str(self.config['transmode'])
        # Bit 5 - Enable enable_repeater
        bits += str(self.config['repeater'])
        # Bit 4 - LBT enable
        bits += str(self.config['lbt'])
        # Bit 3 - WOR transceiver control
        bits += str(self.config['worctrl'])
        # Bits 2:0 - WOR cycle
        bits += '{0:03b}'.format(self.config['wutime'])
        #print("REG3:", bits)
        message.append(int(bits))
        return message
    

    def showConfig(self):
        ''' Show the config parameters of the ebyte E22 LoRa module on the shell '''
        print('=================== CONFIG =====================')
        print('model       \tE22-%s'%(self.config['model']))
        print('frequency   \t%dMhz'%(self.config['frequency']))
        # ADDH/ADDL
        print('address     \t0x%04x'%(self.config['address']))
        # NETID
        print('network id  \t0x%02x'%(self.config['netid']))
        # REG2
        print('channel     \t0x%02x'%(self.config['channel']))
        # REG0
        print('datarate    \t%sbps'%(self.config['datarate']))                
        print('port        \t%s'%(self.config['port']))
        print('baudrate    \t%dbps'%(self.config['baudrate']))
        print('parity      \t%s'%(self.config['parity']))
        # REG1
        print('sub packet  \t%s'%(ebyteE22.SUBPCKT.get(self.config['subpckt'])))
        print('amb. noise  \t%d'%(self.config['amb_noise']))
        print('tx power    \t%s'%(ebyteE22.TXPOWER.get(self.config['txpower'])))     
        # REG3
        print('rssi        \t%s'%(ebyteE22.RSSI.get(self.config['rssi'])))
        print('repeater    \t%s'%(ebyteE22.REPEATER.get(self.config['repeater'])))
        print('transmission\t%s'%(ebyteE22.TRANSMODE.get(self.config['transmode'])))
        print('lbt         \t%s'%(ebyteE22.LBT.get(self.config['lbt'])))
        print('WOR control \t%s'%(ebyteE22.WORCTRL.get(self.config['worctrl'])))
        print('WOR cycle   \t%s'%(ebyteE22.WUTIME.get(self.config['wutime'])))
        print('================================================')

    def showPID(self):
        ''' Get config parameters from the ebyte E22 LoRa module '''
        try:
            # send the command
            result = self.sendCommand('getPID')
            # check result
            if len(result) != 10:
                return "NOK"
            print('product id: 0x{}'.format(binascii.hexlify(result[3:]).decode('ascii')))
            return "OK"

        except Exception as E:
            if self.debug:
                print('Error on getConfig: ',E)
            return "NOK"  

        
    def waitForDeviceIdle(self,timeout=200):
        ''' Wait for the E22 LoRa module to become idle (AUX pin high) '''
        count = timeout//10
        while not self.AUX.value():
            # maximum wait time 200 ms by default
            # FIXME probably the timeout should depend on
            # the airdatarate, as long packets in
            # low data rates can keep the device busy a long time????

            if count == 0:
                print('waitForDeviceIdle(): TIMEOUT!')
                break
            # sleep for 10 ms
            utime.sleep_ms(10)
            # decrement count
            count -= 1

            
            
    def saveConfigToJson(self):
        ''' Save config dictionary to JSON file ''' 
        with open('E22config.json', 'w') as outfile:  
            ujson.dump(self.config, outfile)    


    def loadConfigFromJson(self):
        ''' Load config dictionary from JSON file ''' 
        with open('E22config.json', 'r') as infile:
            result = ujson.load(infile)
        print(self.config)
        
    
    def calcFrequency(self):
        ''' Calculate the frequency (= (minimum frequency + channel) * 1MHz)'''
        freq = self.minfreq + self.config['channel']
        self.config['frequency'] = freq

        
    def setTransmissionMode(self, transmode):
        ''' Set the transmission mode of the E22 LoRa module '''
        if transmode != self.config['transmode']:
            self.config['transmode'] = transmode
            self.setConfig('setConfigPwrDwnSave')
            
            
    def setConfig(self, save_cmd):
        ''' Set config parameters for the ebyte E22 LoRa module '''
        try:
            # send the command
            result = self.sendCommand(save_cmd)
            # check result
            if len(result) != 10:
                return "NOK"
            # debug
            if self.debug:
                # decode result
                self.decodeConfig(result)
                # show config
                self.showConfig()
            # save config to json file
            self.saveConfigToJson()
            return "OK"
        
        except Exception as E:
            if self.debug:
                print('Error on setConfig: ',E)
            return "NOK"  


    def setOperationMode(self, mode):
        ''' Set operation mode of the E32 LoRa module '''
        self.waitForDeviceIdle()
        # get operation mode settings (default normal)
        bits = ebyteE22.OPERMODE.get(mode, '00')
        #if self.debug:
        #print("setOperationMode(): ", bits[1], bits[0])
        # set operation mode
        self.M0.value(int(bits[0]))
        self.M1.value(int(bits[1]))
        self.waitForDeviceIdle()
        # wait a moment
        utime.sleep_ms(50)
        
    
