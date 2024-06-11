This guys code works on pi zero

https://github.com/chandrawi/LoRaRF-Python/tree/main


Execute 

vrishabkakade@sandboxpizero:~/LoRaRF-Python $ python receiver.py


All the required changes are made in this file. The receiver address and frequency needed to be changed



### Installation as per developers readme. Just putting it in here for my reference.
Using pip
Using terminal run following command.

pip3 install LoRaRF
Using Git and Build Package
To using latest update of the library, you can clone then build python package manually. Using this method require setuptools and wheel module.

git clone https://github.com/chandrawi/LoRaRF-Python.git
cd LoRaRF-Python
python3 setup.py bdist_wheel
pip3 install dist/LoRaRF-1.4.0-py3-none-any.whl
