# BYOWS_RPI : WeeWx Driver Implementation of the Build your own WeatherStation Guide Produced by the
# Raspberry Pi Organization with custom LoRa implementation
# GitHub repo:
# Based on the work done by Jardi Martinez - https://github.com/jardiamj/BYOWS_RPi


import configobj
from setup import ExtensionInstaller
from io import StringIO


# ----- Extension Information -----
VERSION = "0.1"
NAME = 'byows_rpi_lora'
PACKAGE_DESCRIPTION = 'Bring Your Own Weather Station (BYOWS) Driver for the Raspberry Pi with LoRa'
AUTHOR = "Vrishab Kakade"
AUTHOR_EMAIL = "vrishabkakade@gmail.com"

# ----- Extension File List -----
filelist = [('bin/user', ['bin/user/byows_rpi_lora.py']),
            ('bin/user/LoRaRF', ['bin/user/LoRaRF/__init__.py',
                                 'bin/user/LoRaRF/base.py',
                                 'bin/user/LoRaRF/SX127x.py',
                                 'bin/user/LoRaRF/SX126x.py'])
            ]

# ----- Configuration details for Weewx.conf -----

driver_config = """
#######################################################################################
# This section is for the Raspberry Pi Bring Your Own Weather Station driver with LoRa.
#######################################################################################
[BYOWS_LORA]
    # This section is for the Raspberry Pi Bring Your Own Weather Station driver with LoRa.
    # [REQUIRED]
    # The driver to use.
    driver = user.byows_rpi_lora
    loop_interval = 2.5


"""

config_dict = configobj.ConfigObj(StringIO(driver_config))


# ----- Extension Loader (Using Generic WeeWX Extension Installer) -----
def loader():
    return WeeEXTInstaller()


class WeeEXTInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeeEXTInstaller, self).__init__(
            version=VERSION,
            name=NAME,
            description=PACKAGE_DESCRIPTION,
            author=AUTHOR,
            author_email=AUTHOR_EMAIL,
            files=filelist,
            config=config_dict
        )
