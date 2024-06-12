"""
This is a weeWX driver implementation of the Build Your OWN Weather
Station using the Raspberry Pi:
https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/

The project has been further enhanced to implement LoRa for wireless transmission of data.
This program receives the data from the LoRa sender (server) and stores the data in Weewx that runs on the Raspberry Pi.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""

__author__ = "Vrishab Kakade"
__contact__ = "vrishabkakade@gmail.com"
__copyright__ = "Copyright $YEAR, $COMPANY_NAME"
__credits__ = ["Jardi A. Martinez Jordan", "Jaganmayi Himamshu"]
__date__ = "2024/06/11"
__deprecated__ = False
__email__ = "vrishabkakade@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "developer"
__status__ = "Production"
__version__ = "0.1"

import datetime
import glob
import logging  # This supports the new WeeWX 4.x logging methodology
import math
import os
import sys
import syslog
import time

import weewx.drivers
# sys.path.insert(1, '/etc/weewx/bin/user') # Alternate path to place the LoRaRF folder
# LoRaRF can also be placed in /usr/share/weewx/
# It should read this from [/etc/weewx/bin]/user/LoRaRF
from .LoRaRF import SX127x, LoRaSpi, LoRaGpio

DRIVER_NAME = "BYOWS_LORA"
DRIVER_VERSION = "0.1"

# Initialize the logger for this module
log = logging.getLogger(__name__)


def loader(config_dict, _):
    return ByowsRpi(**config_dict[DRIVER_NAME])


"""
def confeditor_loader():
    return ByowsRpiConfEditor()
"""


class ByowsRpi(weewx.drivers.AbstractDevice):
    """weewx driver for the Build Your Own Weather Station - Raspberry Pi

    """

    def __init__(self, **stn_dict):
        self.hardware = stn_dict.get("hardware", "BYOWS - Raspberry Pi")
        self.loop_interval = float(stn_dict.get("loop_interval", 5))
        params = dict()
        log.info("using driver %s" % DRIVER_NAME)
        log.info("driver version is %s" % DRIVER_VERSION)
        self.station = ByowsRpiStation(**params)

    @property
    def hardware_name(self):
        return self.hardware

    def genLoopPackets(self):
        """ Function that generates packets for weeWX by looping through station
        data generator function. """
        while True:
            packet = {"dateTime": int(time.time() + 0.5), "usUnits": weewx.METRIC}
            data = self.station.get_data()
            if data != 1:
                packet.update(data)
                yield packet
                time.sleep(self.loop_interval)  # defaults to 5 seconds
            else:
                continue


class ByowsRpiStation(object):
    """ Object that represents a BYOWS_Station. """

    def __init__(self, **params):
        """ Initialize Object. """

    def get_data(self):
        """ Generates data packets every time interval. """

        currentdir = os.path.dirname(os.path.realpath(__file__))
        sys.path.append(os.path.dirname(os.path.dirname(currentdir)))

        # Define the data packet size we expect to receive.
        # This will be used to check against junk packets and discard them
        # Adjust the expected packet size depending on the data being received.
        # For BME280 sensor values, we expect 12 payload length for data and 1 for header.
        expected_data_length = 12

        # Begin LoRa radio with connected SPI bus and IO pins (cs and reset) on GPIO
        # SPI is defined by bus ID and cs ID and IO pins defined by chip and offset number
        spi = LoRaSpi(0, 0)
        cs = LoRaGpio(0, 8)
        reset = LoRaGpio(0, 24)
        LoRa = SX127x(spi, cs, reset)
        res = []
        # print("Begin LoRa radio")
        if not LoRa.begin():
            raise Exception("Something wrong, can't begin LoRa radio")

        # Set frequency to 433 Mhz

        # print("Set frequency to 433 Mhz")
        LoRa.setFrequency(433000000)

        # Set RX gain. RX gain option are power saving gain or boosted gain
        # print("Set RX gain to power saving gain")
        LoRa.setRxGain(LoRa.RX_GAIN_POWER_SAVING, LoRa.RX_GAIN_AUTO)  # AGC on, Power saving gain

        # Configure modulation parameter including spreading factor (SF), bandwidth (BW), and coding rate (CR)
        # Receiver must have same SF and BW setting with transmitter to be able to receive LoRa packet
        # print("Set modulation parameters:\n\tSpreading factor = 7\n\tBandwidth = 125 kHz\n\tCoding rate = 4/5")
        LoRa.setSpreadingFactor(7)  # LoRa spreading factor: 7
        LoRa.setBandwidth(125000)  # Bandwidth: 125 kHz
        LoRa.setCodeRate(5)  # Coding rate: 4/5

        # Configure packet parameter including header type, preamble length, payload length, and CRC type
        # The explicit packet includes header contain CR, number of byte, and CRC type
        # Receiver can receive packet with different CR and packet parameters in explicit header mode
        # print("Set packet parameters:\n\tExplicit header type\n\tPreamble length = 12\n\tPayload Length =",
        #      expected_data_length + 1, "\n\tCRC on")
        LoRa.setHeaderType(LoRa.HEADER_EXPLICIT)  # Explicit header mode
        LoRa.setPreambleLength(12)  # Set preamble length to 12
        LoRa.setPayloadLength(expected_data_length + 1)  # Initialize payloadLength to the expected data + 1 for header
        LoRa.setCrcEnable(True)  # Set CRC enable

        # Set synchronize word for public network (0x14).
        # Others that work are 0x10, 0x15, 0x13 as per the sender's configuration
        # print("Set synchronize word to 0x14")
        # LoRa.setSyncWord(0x10)
        LoRa.setSyncWord(0x14)
        # LoRa.setSyncWord(0x15)
        # LoRa.setSyncWord(0x13)

        # print("\n-- LoRa Receiver --\n")

        # Request for receiving new LoRa packet
        LoRa.request()
        # Wait for incoming LoRa packet
        LoRa.wait()

        # Put received packet to message and counter variable
        # read() and available() method must be called after request() or listen() method
        message = []
        # available() method return remaining received payload length and
        # will decrement each read() or get() method called
        while LoRa.available() > 1:
            # message += chr(LoRa.read()) # This is used if the data is a string
            message += [(LoRa.read())]  # Using this as all our data being received is bytes and int
        counter = [LoRa.read()]  # Read the last byte
        message += counter  # Append the last byte to the message

        # Print packet/signal status including RSSI, SNR, and signalRSSI
        print("Packet status: RSSI = {0:0.2f} dBm | SNR = {1:0.2f} dB".format(LoRa.packetRssi(), LoRa.snr()))

        """
        ==================
        Section to decode the message as the message received will be in bytes (int)
        ==================
        """

        """
        Skip the first element in message as that is the header which shows the count of the packet.
        It is used to see what packets have been dropped
        """
        message_no_header = message[1:]

        # Check against the expected packet size
        # If the packet size (message) is not as expected, skip processing this packet
        if len(message_no_header) != expected_data_length:
            print("Mostly junk data received. Skipping this packet")
            return 1

        # Get 2 elements at a time to decode the value to int from 2 int array
        lg = len(message_no_header)
        lg = lg - 1  # Decrement length by 1 as we start the count from 0
        tup = tuple()
        decoded_tup = []
        for k in range(0, lg, 2):
            tup = [message_no_header[k], message_no_header[k + 1]]
            # Getting single int from 2 array byte
            decoded_tup += [int.from_bytes(tup, byteorder='big', signed=True)]

        # Converting the int to float as decoded_tup is now in int format converted from bytes
        float_value = []
        lx = len(decoded_tup)
        lx = lx - 1  # Decrement length by 1 as we start the count from 0
        # First convert the int to string so that we can add the decimal point
        for k2 in range(0, lx, 2):
            d2 = decoded_tup[k2 + 1]
            # https://www.geeksforgeeks.org/how-to-add-leading-zeros-to-a-number-in-python/
            # Adding leading 0 that was stripped off for the decimal on the sender side
            tup2 = str(decoded_tup[k2]) + '.' + str(d2).rjust(2,
                                                              '0')
            float_value += [tup2]

        # Sometimes junk data is sent in packets and this might lead to negative numbers after the decimal point.
        # To avoid the program from stopping, I use the try except block to continue even if the data is incorrect
        try:
            # Converting the string to float
            res = [float(ele) for ele in float_value]
            print(message[0], "Temperature: ", res[0], "C", "Pressure: ", res[1], "hPa", "Humidity :", res[2], "%")
        except Exception as exc:
            print('[!!!] {err}'.format(err=exc))

        # Show received status in case CRC or header error occur
        status = LoRa.status()
        if status == LoRa.STATUS_CRC_ERR:
            print("CRC error")
        elif status == LoRa.STATUS_HEADER_ERR:
            print("Packet header error")

        data = dict()
        data["outHumidity"] = res[2]
        data["pressure"] = res[1]
        data["outTemp"] = res[0]
        # data["soilTemp1"] = self.get_soil_temp()
        # data["windSpeed"] = float(wind_speed)
        # data["windDir"] = wind_dir
        # data["rain"] = float(self.get_rainfall())
        # data["anemRotations"] = anem_rotations
        # data["timeAnemInterval"] = time_interval
        return data
