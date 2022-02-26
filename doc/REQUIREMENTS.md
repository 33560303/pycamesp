[Main page](/README.md) | [CamFlasher](/doc/CAMFLASHER.md)

# Requirements

Micropython on ESP32 does not leave much space in RAM, a SPIRAM is recommended.

Despite everything, the servers, the shell, the text editor can operate on an ESP32 without spiram, 
it is necessary to generate the firmware embedding the python scripts, in this case less memory is consumed.

For motion capture you absolutely need an ESP32CAM.

Homekit cannot work with the camera on ESP32CAM, problem of insufficient memory to store the stack. Homekit seems to work on Esp32 generic.
# Devices supported

Below are the devices compatible with pycameresp :

![ESP32CAM](/images/Device_ESP32CAM.jpg "ESP32CAM")
![ESP32CAM-MB](/images/Device_ESP32CAM-MB.jpg "ESP32CAM-MB")
![NODEMCU](/images/Device_NODEMCU.jpg "NODE MCU") ![LOLIN32](/images/Device_LOLIN32.jpg "LOLIN32")
![TTGO](/images/Device_TTGO.jpg "TTGO")