"""
Short description of this Python module.
This program is used to send data on a LoRa connected Raspberry Pi Pico (server) to LoRa connected Raspberry Pi Zero 2W
receiver (client)

Longer description of this module.
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.

Usage:
    python main.py

Dependencies:
    ulora.py - used to send the data
    bme280.py - to read the temperature, pressure and humidity settings from BME 280 sensor

Prerequisites:
    1. LoRa SX127x module is connected to Raspberry Pi Pico Using the below

    Semtech SX127x	Raspberry Pi
	VCC	            3.3V
	GND	            GND
	SCK	            GPIO 6
	MISO	        GPIO 4
	MOSI	        GPIO 7
	NSS	            GPIO 5
	RESET	        GPIO 27 (I didn't need to use this)
	DIO1	        -1 (unused)

	2. This LoRa sender (server) that is sending data in the format
    Example:
    [1,       0, 24,                0, 81,                3, 112,                   0, 69,
    0, 66,                   0, 90]
    [packet#, byte_array, temp_d1,  byte_array, temp_d2,  byte_array, pressure_d1,  byte_array, pressure_d2,
    byte_array, humidity_d1, byte_array, humidity_d2]

    Integer is 32 bits (4*8 bits array), so I should really be using 4 array ([1,2,3,4]) for the int values instead of 2
     array ([1,2]). But the numbers I use aren't going to be very large, so to save on memory and bandwidth,
     I will only use the two bits. Change 2 to 4 if the numbers need to be larger

Changelog:
    Version     Changes
    1           Initial Release


LoRa code got from https://github.com/martynwheeler/u-lora.git
"""

__author__ = "Vrishab Kakade"
__contact__ = "vrishabkakade@gmail.com"
__copyright__ = "Copyright $YEAR, $COMPANY_NAME"
__credits__ = ["Martyn Wheeler", "Jaganmayi Himamshu"]
__date__ = "2024/06/11"
__deprecated__ = False
__email__ = "vrishabkakade@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "developer"
__status__ = "Production"
__version__ = "0.1"

from time import sleep
from ulora import LoRa, ModemConfig, SPIConfig
from machine import Pin, I2C
import bme280
import time

led = Pin("LED", Pin.OUT)

# initialize I2C
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)

# Lora Parameters
RFM95_RST = 27
RFM95_SPIBUS = SPIConfig.rp2_0
RFM95_CS = 5
RFM95_INT = 28
RF95_FREQ = 433.0
RF95_POW = 20
CLIENT_ADDRESS = 1
SERVER_ADDRESS = 2

# initialise radio
lora = LoRa(RFM95_SPIBUS, RFM95_INT, CLIENT_ADDRESS, RFM95_CS, reset_pin=RFM95_RST, freq=RF95_FREQ, tx_power=RF95_POW,
            acks=True)

# loop and send data
while True:
    # Turn on led to make sure there is a connection. Only used for troubleshooting.
    # led.on()
    bme = bme280.BME280(i2c=i2c)
    # Below gets the values as is i.e. int or string depending on teh return type of values
    # temp = bme.values[0]
    # pressure = bme.values[1]
    # humidity = bme.values[2]
    # reading = 'Temperature: ' + temp + '. Humidity: ' + humidity + '. Pressure: ' + pressure

    """
    Reason for converting to byte from int:
    https://www.geeksforgeeks.org/how-to-convert-int-to-bytes-in-python/
    I had to convert the data to bytes from int as there is a limitation of not being able to send an integer
    larger than 255 due to the byte size. So using bytes of 2, I can send much larger number.
    The format of the output will be [0, number-up-to-255] [1, number>255<510] and so on.
    This will have to be decoded on the receiver side. Example 256 will be [1, 0] 257 will be [1, 1]
    
    Reason for not using float:
    Since I can't send float, I am sending separating the numbers before and after the decimal point and sending them 
    separately.
    Example: temperature of 24.81 will be int of 24 (temp_d1) and 81 (temp_d2).
    Only thing to remember on the receiver side is numbers less than 10 for the decimal will be sent without the 
    leading 0.
    So on the receiver this check must be done and leading zero will have to be included.
    
    Format of the data being sent
    Example:
    [1,       0, 24,                0, 81,                3, 112,                   0, 69,                    
    0, 66,                   0, 90]
    [packet#, byte_array, temp_d1,  byte_array, temp_d2,  byte_array, pressure_d1,  byte_array, pressure_d2,  
    byte_array, humidity_d1, byte_array, humidity_d2]
    
    Integer is 32 bits (4*8 bits array), so I should really be using 4 array ([1,2,3,4]) for the int values instead of 
    2 array ([1,2]). But the numbers I use aren't going
    to be very large, so to save on memory and bandwidth, I will only use the two bits. Change 2 to 4 if the numbers 
    need to be larger
    """

    temp_d1 = bme.values[0].to_bytes(2, 'big')  # Change 2 to 4 if the number needs to be larger
    temp_d2 = bme.values[1].to_bytes(2, 'big')
    pressure_d1 = bme.values[2].to_bytes(2, 'big')
    pressure_d2 = bme.values[3].to_bytes(2, 'big')
    humidity_d1 = bme.values[4].to_bytes(2, 'big')
    humidity_d2 = bme.values[5].to_bytes(2, 'big')
    # reading = 'Temperature: ' + temp + '. Humidity: ' + humidity + '. Pressure: ' + pressure
    reading = [temp_d1, temp_d2, pressure_d1, pressure_d2, humidity_d1, humidity_d2]

    lora.send_to_wait(reading, SERVER_ADDRESS)  # Sending the readings
    sleep(2.5)
