###############################################################################
# MicroPython LoRa RSSI/Range Test - LoRa Receiver with GPS Module 
# (Tested with ESP32-WROOM-32) 
#
# The receiver's position and a timestamp are decoded from NMEA messages
# received via UART.
#
# If available, LoRa messages are received from the ebyteE22 LoRa transceiver
# module via another UART. If the messages expected from the LoRa transmitter
# could not be received for a certain time, an rssi value of -255 is assumed,
# indicating loss of the LoRa radio link.
#
# At a defined interval (if a valid position is available), a tuple
# <timestamp>, <latitude>, <longitude>, <altitude>, <rssi>
# is printed and optionally written to a log file.
# 
# If logging is enabled, a filename in the format
# "log_<8_random_hex_digits_>.csv" is created after power-on or reset.
# The log files are written to MicroPython's internal file system.
# Logging must be stopped explicitly, otherwise the file cannot be closed
# properly and will be corrupt/empty.
#
# Log files can be converted from CSV-format to a suitable format -
# such as GPX or KML - on the host later.
#
# Two LEDs indicate the state of the GPS fix and the LoRa link, respectively.
#
# However, the coding style is kind of quick and dirty...
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
# 20211018 initial release
#
######################################################################

from machine import Pin, UART
from micropyGPS import MicropyGPS
from loraE22 import ebyteE22
import machine
import ubinascii
import time
import os

DEBUG = False
LOGGING = True

me   = 1
peer = 0
addr = [0x0000, 0x0001]
chan = [0x00, 0x00]

M0pin        = 25                       # loraE22 M0 pin
M1pin        = 26                       # loraE22 M1 pin
AUXpin       = 14                       # loraE22 AUX pin
TXpin        = 32                       # GPS UART TX pin (not used)
RXpin        = 35                       # GPS UART RX pin
LEDGNpin     = 33                       # green LED pin - GPS fix valid
LEDBLpin     = 2                        # blue LED pin - LoRa TX valid
KEYpin       = 0                        # 'BOOT' key pin - stop logging 
BAUDRATE     = 4800                     # GPS baudrate
LORA_TO      = 5000                     # LoRa RX timeout (ms)
LORA_RXLOST  = -255                     # RSSI indicating reception lost
LOG_INTERVAL = 30                       # Logging interval (s)
TX_ID        = 'ESP32 ID: 240ac462553c' # expected Lora Message content - Transmitter ID

# optional replacement for buggy NMEA date string from HI-203E GPS module
#GPS_DATE    = None
GPS_DATE     = '2021-10-18'

gps    = None
led_gn = Pin(LEDGNpin, Pin.OUT, value=0)
led_bl = Pin(LEDBLpin, Pin.OUT, value=0)
key    = Pin(KEYpin, Pin.IN)


def print_dbg(text):
    """
    Print debug messages - only in DEBUG == True

    Parameters:
        text (string):    text to be printed
    """
    if DEBUG:
        print(text)


def timestamp():
    """
    Generate UTC timestamp as used by KML and gpx (<YYYY>-<MM>-<DD>T<hh>:<mm>:<ss.sss>Z)

    If defined, GPS_DATE is used instead of the date retrieved from NMEA RMC message -
    workaround for a buggy GPS module.
    
    Returns:    UTC timestamp
    """
    if GPS_DATE:
        ts = GPS_DATE
    else:
        ts = "{}-{:02d}-{:02d}".format(2000 + gps.date[2], gps.date[1], gps.date[0])
    ts = ts + "T{:02d}:{:02d}:{:06.3f}Z".format(gps.timestamp[0], gps.timestamp[1], gps.timestamp[2])
    return ts


def gen_filename():
    """
    Generate filename from GPS date and time data (<YYYY><MM><DD>_T<hh><mm><ss>Z.csv)

    Returns:    filename
    """
    if GPS_DATE:
        ts = GPS_DATE
    else:
        ts = "{}{:02d}{:02d}_".format(2000 + gps.date[2], gps.date[1], gps.date[0])
    ts = ts + "T{:02d}{:02d}{:02d}Z.csv".format(gps.timestamp[0], gps.timestamp[1], gps.timestamp[2])
    return ts
    
    
def gps_log_due(log_ts):
    """
    Check if GPS logging interval has expired by comparing
    previous and current NMEA timestamp with LOG_INTERVAL

    Parameters:
        log_ts (int):    timestamp (seconds since midnight)

    Returns:    True  Logging interval expired
                False Logging interval not expired yet
    """
    if log_ts == None:
        return True
    now = gps.timestamp[0] * 3600 + gps.timestamp[1] * 60 + gps.timestamp[2]
    if now < log_ts:
        return True 
    else:
        return (now - log_ts) > LOG_INTERVAL

# Main procedure - wrapped in a function in order to be executed in "with open() ..." context (see below)  
def main():
    global gps
        
    green = False

    e22 = ebyteE22(M0pin, M1pin, AUXpin, Port='U2', Address=addr[me], Channel=chan[me], debug=False)

    # enable appending of RSSI to RX message
    e22.config['rssi'] = 1

    e22.start()

    serdev = UART(1, BAUDRATE, rx=RXpin, tx=TXpin)

    # Instantiate the micropyGPS object
    gps = MicropyGPS(location_formatting='dd')

    lora_deadline = 0
    log_ts = None
    stat = None
    while True:
        if LOGGING and key.value() == 0:
            # Stop logging
            return
        
        # Poll LoRa module receive buffer
        rx_msg = e22.recvMessage(addr[peer], chan[peer], useChecksum=True)
        if ('rssi' in rx_msg and 'msg' in rx_msg and rx_msg['rssi'] and TX_ID in rx_msg['msg']):
            # Proper message with expected payload and valid RSSI received
            print_dbg("Node {} RX: address {} - channel {} - message {}".format(me, addr[peer], chan[peer], rx_msg))
            led_bl.value(1)
            rssi = rx_msg['rssi']
            lora_deadline = time.ticks_add(time.ticks_ms(), LORA_TO)
        else:
            if time.ticks_diff(lora_deadline, time.ticks_ms()) < 0:
                # No valid data received for some time
                led_bl.value(0)
                rssi = LORA_RXLOST

        if serdev.any():
            # Read and process NMEA data
            rdata = serdev.read(1)
            try:
                stat = gps.update(rdata.decode('utf-8'))
            except UnicodeError as e:
                pass
            
            if stat:
                # Got new NMEA message    
                stat = None
                print_dbg("{}/{}".format(gps.fix_stat, gps.fix_type))
                #if gps.fix_type == gps.__FIX_3D:
                if gps.fix_stat and (gps.fix_type != gps.__NO_FIX):
                    # Valid position
                    led_gn.value(1)
                    if gps_log_due(log_ts):
                        # Logging interval has passed
                        log_data = "{},{},{},{},{}".format(timestamp(),
                                                           gps.latitude_string(),
                                                           gps.longitude_string(),
                                                           gps.altitude, rssi)
                        print(log_data)
                        if LOGGING:
                            f.write(log_data + '\n')
                        log_ts = gps.timestamp[0] * 3600 + gps.timestamp[1] * 60 + gps.timestamp[2]
                else:
                    # No valid position
                    led_gn.value(0)


if LOGGING:
    # Logging and printing
    filename = "log_" + ubinascii.hexlify(os.urandom(4)).decode('ascii') + ".csv"
    print("Logfile: ", filename)
    print("Press 'BOOT' key to stop logging, otherwise file may be corrupt!")
    with open(filename, 'w') as f:
        main()
    print("Logging finished.")
    
    # Flash LEDs
    for i in range(20):
        led_bl.value(1)
        led_gn.value(1)
        time.sleep_ms(100)
        led_bl.value(0)
        led_gn.value(0)
        time.sleep_ms(100)
    
    # Loop forever
    while True:
        machine.idle()

else:
    # No logging, just printing
    main()
