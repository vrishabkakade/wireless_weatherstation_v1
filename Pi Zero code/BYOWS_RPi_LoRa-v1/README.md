# Introduction

byows_rpi_lora - This is an weeWX driver implementation of the Build Your Own Weather
Station guide produced by the [Raspberry Pi Organization](https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/)

The project has been further enhanced to implement LoRa for wireless transmission of data.
This program receives the data from the LoRa sender (server) and stores the data in Weewx which runs on the Raspberry Pi.

Distributed under terms of the GPLv3

# Installation

Download the file BYOWS_RPi_LoRa-v1.zip

Run the command
weectl extension install BYOWS_RPi_LoRa-v1.zip (or use sudo in case the installation was done as root)

Update weewx.conf (usually in /etc/weewx/weewx.conf)
Change the station type to BYOWS_LORA
station_type = BYOWS_LORA
