import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(currentdir)))
from LoRaRF import SX127x, LoRaSpi, LoRaGpio
import time

# Begin LoRa radio with connected SPI bus and IO pins (cs and reset) on GPIO
# SPI is defined by bus ID and cs ID and IO pins defined by chip and offset number
spi = LoRaSpi(0, 0)
cs = LoRaGpio(0, 8)
reset = LoRaGpio(0, 24)
irq = LoRaGpio(0, 17)
#LoRa = SX127x(spi, cs, reset, irq)
LoRa = SX127x(spi, cs, reset)
print("Begin LoRa radio")
if not LoRa.begin() :
    raise Exception("Something wrong, can't begin LoRa radio")

# Set frequency to 915 Mhz
print("Set frequency to 915 Mhz")
LoRa.setFrequency(433000000)

# Set RX gain to boosted gain
print("Set RX gain to boosted gain")
LoRa.setRxGain(LoRa.RX_GAIN_BOOSTED, LoRa.RX_GAIN_AUTO)

# Configure modulation parameter including spreading factor (SF), bandwidth (BW), and coding rate (CR)
print("Set modulation parameters:\n\tSpreading factor = 7\n\tBandwidth = 125 kHz\n\tCoding rate = 4/5")
LoRa.setSpreadingFactor(7)
LoRa.setBandwidth(125000)
LoRa.setCodeRate(5)

# Configure packet parameter including header type, preamble length, payload length, and CRC type
print("Set packet parameters:\n\tExplicit header type\n\tPreamble length = 12\n\tPayload Length = 15\n\tCRC on")
LoRa.setHeaderType(LoRa.HEADER_EXPLICIT)
LoRa.setPreambleLength(35)
LoRa.setPayloadLength(65)
LoRa.setCrcEnable(True)

# Set syncronize word for public network (0x34)
print("Set syncronize word to 0x34")
LoRa.setSyncWord(0x13)

print("\n-- LoRa Receiver Callback --\n")


# receive data container
packetData = ()

def getReceiveData() :

    global packetData
    # Store received data
    packetData = LoRa.read(LoRa.available())

# Register callback function to be called every RX done
LoRa.onReceive(getReceiveData)
print(packetData)

# Request for receiving new LoRa packet in RX continuous mode
LoRa.request(LoRa.RX_CONTINUOUS)

# Receive message continuously
while True :
    if packetData :


        # Print received message and counter in serial
        length = len(packetData) - 1
        message = ""
        for i in range(length) :
            message += chr(packetData[i])
        counter = packetData[length]
        print(f"{message}  {counter}")

        # Print packet/signal status including RSSI, SNR, and signalRSSI
        print("Packet status: RSSI = {0:0.2f} dBm | SNR = {1:0.2f} dB".format(LoRa.packetRssi(), LoRa.snr()))

        # Reset receive data container
        packetData = ()
