"""
Measure rainfall with the bucket connected to Pico
"""
from machine import Pin, I2C

led = Pin("LED", Pin.OUT)
rainInput = Pin(3, Pin.IN, Pin.PULL_UP)  # Pin 5, GP 3 and other to ground. Order doesn't matter
rainFlag = 0
rainCount = 0

while True:
    # Rain Gauge
    # Code got from
    # https://bc-robotics.com/tutorials/raspberry-pi-pico-weather-station-part-2-micropython/
    if rainInput.value() == 0 and rainFlag == 1:  # Compare to our flag to look for a LOW transit
        # global rainCount #Ensure we write to the global count variable
        rainCount += 1  # Since the sensor has transited low, increase the count by 1
        # print(rainCount)
        # led.toggle()

    rainFlag = rainInput.value()  # Set our flag to match our input
