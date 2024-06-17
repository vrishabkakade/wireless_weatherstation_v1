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

LoRa code Copyright (c) 2022 Chandra Wijaya Sentosa https://github.com/chandrawi/LoRaRF-Python/tree/main

Raspberry Pi Weather Station driver for Weewx got from Jardi A. Martinez Jordan https://github.com/jardiamj/BYOWS_RPi

Customized by Vrishab Kakade to work for the weather station
"""

__author__ = "Vrishab Kakade"
__contact__ = "vrishabkakade@gmail.com"
__copyright__ = "Copyright $YEAR, $COMPANY_NAME"
__credits__ = ["Jardi A. Martinez Jordan", "Jaganmayi Himamshu", "Chris @ BC-Robotics", "Chandra Wijaya Sentosa"]
__date__ = "2024/06/11"
__deprecated__ = False
__email__ = "vrishabkakade@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "developer"
__status__ = "Production"
__version__ = "1"

import logging  # This supports the new WeeWX 4.x logging methodology
import math
import os
import sys
import time
import numpy as np

import weewx.drivers
# sys.path.insert(1, '/etc/weewx/bin/user') # Alternate path to place the LoRaRF folder
# LoRaRF can also be placed in /usr/share/weewx/
# It should read this from [/etc/weewx/bin]/user/LoRaRF
from .LoRaRF import SX127x, LoRaSpi, LoRaGpio

DRIVER_NAME = "BYOWS_LORA"
DRIVER_VERSION = "1"

# Initialize the logger for this module
log = logging.getLogger(__name__)

# Setting up the possible range of RSSI values as per local testing and https://lora.readthedocs.io/en/latest/
RSSI_range = np.arange(-45, -121, -1)


def loader(config_dict, _):
    return ByowsRpi(**config_dict[DRIVER_NAME])


"""
def confeditor_loader():
    return ByowsRpiConfEditor()
"""


class ByowsRpi(weewx.drivers.AbstractDevice):
    """weewx driver for the Build Your Own Weather Station - Raspberry Pi with LoRa

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
            if data is not None:
                packet.update(data)
                yield packet
                time.sleep(self.loop_interval)  # defaults to 5 seconds
            else:
                continue


def get_rainfall(bucket_tips):
    """ Returns rainfall in cm. """
    bucket_size = 0.2794  # in mm
    rainfall = (bucket_tips * bucket_size) / 10.0  # Convert to cm
    return rainfall


def read_direction(wind_dir):
    reading = wind_dir * 4
    if 876 <= reading <= 900:
        s = 112.5
    elif 867 <= reading <= 875:
        s = 67.5
    elif 846 <= reading <= 866:
        s = 90.0
    elif 6 <= reading <= 7:
        s = 157.5
    elif 690 <= reading <= 710:
        s = 135.0
    elif 8 <= reading <= 9:
        s = 202.5
    elif 560 <= reading <= 580:
        s = 180.0
    elif 430 <= reading <= 436:
        s = 22.5
    elif 370 <= reading <= 390:
        s = 45.0
    elif 10 <= reading <= 11:
        s = 247.5
    elif 230 <= reading <= 250:
        s = 225.0
    elif 180 <= reading <= 200:
        s = 337.5
    elif 130 <= reading <= 140:
        s = 0.0
    elif 100 <= reading <= 120:
        s = 292.5
    elif 70 <= reading <= 90:
        s = 315.0
    elif 40 <= reading <= 60:
        s = 270.0
    else:
        log.debug("Unknown Wind Vane value: %s" % str(reading))
        return None
    return s


class ByowsRpiStation(object):
    """ Object that represents a BYOWS_Station. """

    def __init__(self, **params):
        """ Initialize Object. """
        self.last_wind_time = time.time()
        self.anemometer_radius_cm = 9.0  # Radius of your anemometer
        self.anemometer_adjustment = 1.18
        self.CM_IN_A_KM = 100000.0
        self.SECS_IN_AN_HOUR = 3600

    def reset_wind(self):
        self.last_wind_time = time.time()

    def calculate_speed(self, time_sec, rotations):
        circumference_cm = (2 * math.pi) * self.anemometer_radius_cm
        rotations = rotations / 2.0
        # Calculate the distance traveled by a cup in km
        dist_km = (circumference_cm * rotations) / self.CM_IN_A_KM
        # Speed = distance / time
        km_per_sec = dist_km / time_sec
        km_per_hour = km_per_sec * self.SECS_IN_AN_HOUR
        # Calculate Speed
        final_speed = km_per_hour * self.anemometer_adjustment
        return final_speed

    def get_wind_speed(self, rotations):
        """ Function that returns wind speed in km/hr. """
        wind_speed = self.calculate_speed(time.time() - self.last_wind_time, rotations)
        self.reset_wind()  # reset last time reading
        return wind_speed

    def get_wind(self, rotations, wind_dir):
        """ Function that returns wind as a vector: speed, direction."""
        return self.get_wind_speed(rotations), read_direction(wind_dir)

    def get_message(self, LoRa):
        # Request for receiving a new LoRa packet
        LoRa.request()
        # Wait for an incoming LoRa packet
        LoRa.wait()

        # Put a received packet to message and counter variable
        # read() and available() method must be called after request() or listen() method
        message = []
        # available() method return remaining received payload length and
        # will decrement each read() or get() method called
        while LoRa.available() > 1:
            # message += chr(LoRa.read()) # This is used if the data is a string
            message += [(LoRa.read())]  # Using this as all our data being received is bytes and int
        counter = [LoRa.read()]  # Read the last byte
        message += counter  # Append the last byte to the message
        return message

    def check_message_length(self, message, expected_data_length):
        if len(message) != expected_data_length + 1:
            print("Mostly junk data received for the first packet. Skipping this packet")
            log.debug("Mostly junk data received for the first packet. Skipping this packet")
            return None

    def get_data(self):
        """ Generates data packets every time interval. """

        currentdir = os.path.dirname(os.path.realpath(__file__))
        sys.path.append(os.path.dirname(os.path.dirname(currentdir)))

        # Define the data packet size we expect to receive.
        # This will be used to check against junk packets and discard them to
        # Adjust the expected packet size depending on the data being received.
        # For BME280 sensor values, we expect 15 payload lengths for data and 1 for header.
        expected_data_length = 15

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

        # Set RX gain. RX gain option is power saving gain or boosted gain
        # print ("Set RX gain to power saving gain")
        LoRa.setRxGain(LoRa.RX_GAIN_POWER_SAVING, LoRa.RX_GAIN_AUTO)  # AGC on, Power saving gain

        # Configure modulation parameter including spreading factor (SF), bandwidth (BW), and coding rate (CR)
        # Receiver must have the same SF and BW setting with transmitter to be able to receive LoRa packet
        # print ("Set modulation parameters:\n\tSpreading factor = 7\n\tBandwidth = 125 kHz\n\tCoding rate = 4/5")
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
        # print ("Set synchronize word to 0x14")
        # LoRa.setSyncWord(0x10)
        LoRa.setSyncWord(0x14)
        # LoRa.setSyncWord(0x15)
        # LoRa.setSyncWord(0x13)

        # print("\n-- LoRa Receiver --\n")

        ##############################
        # Receive the first message
        ##############################
        message = self.get_message(LoRa)

        # If the first packet length is not as expected, skip the entire loop.
        self.check_message_length(message, expected_data_length)

        # The first message should have an odd number header. If not, skip and don't get the next packet
        if message[0] % 2 == 0:
            log.debug("Even number packet for fist message. Skipping")
            log.debug("Message: %s", message)
            return None

        ##############################
        # Receive the second message
        ##############################
        # Receive the same packet twice to ensure no junk data is being received.
        # This will have message[0] + 1 as header number
        message_check = self.get_message(LoRa)

        # If the second packet length is not as expected, skip the entire loop.
        self.check_message_length(message_check, expected_data_length)

        # The second message should have an even number header. If not, skip and don't get the next packet
        if message_check[0] % 2 != 0:
            log.debug("Odd number packet for second message. Skipping")
            log.debug("Message: %s", message_check)
            return None

        """ Packet structure
        Example:
        [(1)1,  (2)0, (3)24,    (4)0, (5)81,    (6)3, (7)112,   (8)0, (9)69,    (10)0, (11)66,  (12)0, (13)90,
        (14)3,  (15)5,  (16)12]]
        [(1)packet header#,    (2)byte_array, (3)temp_d1,      (4)byte_array, (5)temp_d2,
        (6)byte_array, (7)pressure_d1,      (8)byte_array, (9)pressure_d2,      (10)byte_array, (11)humidity_d1,
        (12)byte_array, (13)humidity_d2,    (14)rainfall(bucket tips),          (15)windcount (Anemometer rotations),
        (16)windDir (Wind vane) ]
        """

        # Print packet/signal status including RSSI, SNR, and signalRSSI
        print("Packet status: RSSI = {0:0.2f} dBm | SNR = {1:0.2f} dB".format(LoRa.packetRssi(), LoRa.snr()))
        log.debug("Packet status: RSSI = {0:0.2f} dBm | SNR = {1:0.2f} dB".format(LoRa.packetRssi(), LoRa.snr()))

        # Get the signal strength to store in the database
        # to Get the percentage relative to the values stored in RSSI_range
        # https://stackoverflow.com/questions/53822430/percentage-of-array-between-values
        RSSI = [LoRa.packetRssi()]
        freq = np.histogram(RSSI_range, bins=[-np.inf] + RSSI + [np.inf])[0] / RSSI_range.size
        signal_strength = freq[0] * 100  # Convert to percentage

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
        message_no_header_check = message_check[1:]

        # Debugging - Writing to file to see the raw data being received
        with open("output.log", "a") as debug_log_file:
            print("Raw message received:", message, file=debug_log_file)
            print("Raw message check received:", message_check, file=debug_log_file)
        log.debug("Raw message received: %s", message)
        log.debug("Raw message check received: %s", message_check)

        # Check to make sure both packets received are same. If not discard them.
        # The check message should be the next consecutive package
        if message_check[0] != message[0] + 1:
            log.debug("Check message is not the next one after message. Skipping")
            return None
        if message_no_header != message_no_header_check:
            print("Packets don't match. Skipping this packet")
            log.debug("Packets don't match. Skipping this packet")
            return None

        # Check against the expected packet size
        # If the packet size (message) is not as expected, skip processing this packet
        if len(message_no_header) != expected_data_length:
            print("Mostly junk data received. Skipping this packet")
            log.debug("Mostly junk data received. Skipping this packet")
            return None

        # Get 2 elements at a time to decode the value to int from 2 int arrays
        # lg = len(message_no_header) # Skipping the rain,
        # which is the 13th and 14th element as the processing is done separately.
        # The 15th and 16th elements are for anemometer,
        # The 17th and 18th elements are for Wind Vane.
        lg = 12
        lg = lg - 1  # Decrement length by 1 as we start the count from 0
        # tup = tuple() # Should be a tuple as the received data must not be changed
        decoded_tup = []
        for k in range(0, lg, 2):
            tup = [message_no_header[k], message_no_header[k + 1]]
            # Getting single int from 2 array bytes
            decoded_tup += [int.from_bytes(tup, byteorder='big', signed=True)]

        # Debugging - Writing to file to see where Index out of range error is occurring
        with open("output.log", "a") as debug_log_file:
            print("Undecoded:", message_no_header, file=debug_log_file)
            print("Decoded tup:", decoded_tup, file=debug_log_file)
        log.debug("Undecoded: %s", message_no_header)
        log.debug("Decoded tup: %s", decoded_tup)

        # Converting the int to float as decoded_tup is now in int format converted from bytes
        float_value = []
        lx = len(decoded_tup)
        lx = lx - 1  # Decrement length by 1 as we start the count from 0
        # First, convert the int to string so that we can add the decimal point
        for k2 in range(0, lx, 2):
            d2 = decoded_tup[k2 + 1]
            # https://www.geeksforgeeks.org/how-to-add-leading-zeros-to-a-number-in-python/
            # Adding leading 0 that was stripped off for the decimal on the sender side
            tup2 = str(decoded_tup[k2]) + '.' + str(d2).rjust(2,
                                                              '0')
            float_value += [tup2]

        # To avoid index out of range error, doing an additional check
        if len(float_value) != 3:
            print("Something went wrong in processing the packet. Skipping this packet")
            log.debug("Something went wrong in processing the packet. Skipping this packet")
            return None

        # Sometimes junk data is sent in packets, and this might lead to negative numbers after the decimal point.
        # To avoid the program from stopping, I use the try except block to continue even if the data is incorrect
        try:
            # Converting the string to float
            res = [float(ele) for ele in float_value]
            print(message[0], "Temperature: ", res[0], "C", "Pressure: ", res[1], "hPa", "Humidity :", res[2], "%",
                  "Bucket Tips: ", message_no_header[12], "Wind rotations", message_no_header[13],
                  "Wind Direction:", message_no_header[14], "Signal Strength:", round(signal_strength))
            log.debug("Temperature: %s, Pressure: %s, Humidity: %s, Bucket Tips: %s, Wind rotations:%s, "
                      "Wind Direction: %s, Signal Strength: %s  ", res[0], res[1], res[2], message_no_header[12],
                      message_no_header[13], message_no_header[14], round(signal_strength))

            # Debugging - Writing to file to see where Index out of range error is occurring
            with open("output.log", "a") as debug_log_file:
                print(message[0], "Temperature: ", res[0], "C", "Pressure: ", res[1], "hPa", "Humidity :", res[2], "%",
                      "Bucket Tips: ", message_no_header[12], "Wind rotations", message_no_header[13],
                      "Wind Direction:", message_no_header[14], "len(float_value)", len(float_value),
                      file=debug_log_file)

        except Exception as exc:
            print('[!!!] {err}'.format(err=exc))
            log.debug("Error: %s", '[!!!] {err}'.format(err=exc))
            return None

        # Show received status in case CRC or header error occur
        status = LoRa.status()
        if status == LoRa.STATUS_CRC_ERR:
            print("CRC error")
        elif status == LoRa.STATUS_HEADER_ERR:
            print("Packet header error")

        data = dict()
        anem_rotations = message_no_header[13] / 2.0
        time_interval = self.last_wind_time - time.time()
        wind_speed, wind_dir = self.get_wind(message_no_header[13], message_no_header[14])  # Pass data from pico
        data["outHumidity"] = res[2]
        data["pressure"] = res[1]
        data["outTemp"] = res[0]
        # data["soilTemp1"] = self.get_soil_temp()
        data["windSpeed"] = float(wind_speed)
        data["windDir"] = wind_dir
        data["rain"] = float(get_rainfall(message_no_header[12]))
        data["anemRotations"] = anem_rotations
        data["timeAnemInterval"] = time_interval
        data["rxCheckPercent"] = signal_strength
        return data
