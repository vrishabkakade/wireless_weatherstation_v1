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

    Integer is 32 bits (4*8-bit array), so I should really be using 4 array ([1,2,3,4]) for the int values instead of 2
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
__credits__ = ["Martyn Wheeler", "Jaganmayi Himamshu", "Tony DiCola"]
__date__ = "2024/06/11"
__deprecated__ = False
__email__ = "vrishabkakade@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "developer"
__status__ = "Production"
__version__ = "1"

from time import sleep
from ulora import LoRa, ModemConfig, SPIConfig
from machine import Pin, I2C, ADC
import bme280
import time
import _thread
import utime

terminate = False  # Used to terminate thread https://forums.raspberrypi.com/viewtopic.php?t=366626

spLock = _thread.allocate_lock()  # creating semaphore

led = Pin("LED", Pin.OUT)

# Global count variables
windCount = 0
rainCount = 0

# Wind Vane
windVane = ADC(Pin(26))  # Assign the Wind Vane to ADC0 (Pin 26)

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


def core1_task():
    """Core 1 handles our monitoring of the Rain Gauge and Anemometer and hosts the Core 1 sensors
    (Rain Gauge, Anemometer)"""
    global terminate
    # For rainfall
    rainInput = Pin(3, Pin.IN, Pin.PULL_UP)  # Pin 5, GP 3 and other to ground. Order doesn't matter
    rainFlag = 0

    # Anemometer
    windInput = Pin(8, Pin.IN, Pin.PULL_UP)
    windFlag = 0

    while not terminate:
        spLock.acquire()  # Acquire semaphore lock

        if rainInput.value() == 0 and rainFlag == 1:  # Compare to our flag to look for a LOW transit
            global rainCount  # Ensure we write to the global count variable
            rainCount += 1  # Since the sensor has transited low, increase the count by 1

        rainFlag = rainInput.value()  # Set our flag to match our input

        # Anemometer
        if windInput.value() != 0 or windFlag != 1:
            pass
        else:  # Compare to our flag to look for a LOW transit
            global windCount  # Ensure we write to the global count variable
            windCount += 1  # Since the sensor has transited low, increase the count by 1

        windFlag = windInput.value()  # Set our flag to match our input

        utime.sleep(0.01)  # 0.01 sec or 10us delay
        spLock.release()
    print("New thread is terminating gracefully.")


# Start Core 1
_thread.start_new_thread(core1_task, ())

try:
    # loop and send data
    while True:
        spLock.acquire()  # Acquire semaphore lock
        # Turn on led to make sure there is a connection. Only used for troubleshooting.
        # led.on()
        bme = bme280.BME280(i2c=i2c)
        # Below gets the values as is i.e., int or string depending on the return type of values
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
        Since I can't send float, I am sending separating the numbers before and after the decimal point and 
        sending them 
        separately.
        Example: temperature of 24.81 will be int of 24 (temp_d1) and 81 (temp_d2).
        Only thing to remember on the receiver side is numbers less than 10 for the decimal will be sent without the 
        leading 0.
        So on the receiver this check must be done and leading zero will have to be included.
        
        Format of the data being sent
        Example:
        [(1)1,  (2)0, (3)24,    (4)0, (5)81,    (6)3, (7)112,   (8)0, (9)69,    (10)0, (11)66,  (12)0, (13)90,
        (14)3,  (15)5,  (16)12]]
        [(1)packet header#,    (2)byte_array, (3)temp_d1,      (4)byte_array, (5)temp_d2,  
        (6)byte_array, (7)pressure_d1,      (8)byte_array, (9)pressure_d2,      (10)byte_array, (11)humidity_d1, 
        (12)byte_array, (13)humidity_d2,    (14)rainfall(bucket tips),          (15)windcount (Anemometer rotations), 
        (16)windDir (Wind vane) ]
        
        Integer is 32 bits (4*8 bits array), so I should really be using 4 array ([1,2,3,4]) for the int values 
        instead of 2 array ([1,2]). But the numbers I use aren't going to be very large, so to save on memory and 
        bandwidth, I will only use the two bits. Change 2 to 4 if the numbers need to be larger
        """

        temp_d1 = bme.values[0].to_bytes(2, 'big')  # Change 2 to 4 if the number needs to be larger
        temp_d2 = bme.values[1].to_bytes(2, 'big')
        pressure_d1 = bme.values[2].to_bytes(2, 'big')
        pressure_d2 = bme.values[3].to_bytes(2, 'big')
        humidity_d1 = bme.values[4].to_bytes(2, 'big')
        humidity_d2 = bme.values[5].to_bytes(2, 'big')

        # Rain Gauge
        # Pin numbers and code to use got from
        # https://bc-robotics.com/tutorials/raspberry-pi-pico-weather-station-part-2-micropython/
        # Sending only the number of bucket tips as it is easy to send int over LoRa.
        # I will convert the number of bucket tips to cm on the receiver side as weewx will expect it in cm.
        # Passing 1 byte is enough as the number won't get > 255 in 2.5 sec loop
        rainfall = rainCount.to_bytes(1, 'big')
        rainCount = 0  # Setting it back to zero for the next loop

        # Anemometer
        # Passing 1 byte is enough as the number won't get > 255 in 2.5 sec loop
        windcount = windCount.to_bytes(1, 'big')
        windCount = 0

        # Wind Vane
        windDir = round((windVane.read_u16() / 64) / 4)  # Read A0, convert to 10-bit (0-1023) and further dividing
        # by 4 to get a number < 255 as it is easy to send and decode
        # Passing 1 byte is enough as the number won't get > 255 in 2.5 sec loop
        winddir = windDir.to_bytes(1, 'big')

        reading = [temp_d1, temp_d2, pressure_d1, pressure_d2, humidity_d1, humidity_d2, rainfall, windcount, winddir]

        """
        Readings are sent twice as sometimes junk readings are received on the receiver side. We compare the two
        readings on the receiver side and if they don't match, we discard the packets
        """
        lora.send_to_wait(reading, SERVER_ADDRESS)  # Sending the readings
        lora.send_to_wait(reading, SERVER_ADDRESS)  # Sendinig the readings a second time
        spLock.release()
        sleep(5)

except KeyboardInterrupt:
    terminate = True
    time.sleep(0.3)
    print("Main thread terminated gracefully.")
