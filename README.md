A scanning camera in a giant sewer pipe. A Raspberry Pi camera module without lens is rotated and shifted to cover a 200mm disk. At each position a photo is taken and stitched to a giant image afterwards. Code is functional, hardware works, example images are ... well, not beautiful. On hold for now but might get around to finish this project at some point in the future.

![sewage pipe camera](media/camera.jpg)
![example image](media/example_output.png)

My design is based on the [Lafodis160](http://aggregate.org/DIT/iss070.pdf) an ESP-32 scanning camera by [Henry Dietz and Paul Eberhart](http://aggregate.org).

# flashing GRBL

* The cheap "CNC engraver shield" is not pin-compatible to the standard CNC shield, the STEP and DIR pins for all three axes are switched. Overwrite `pin_map.h` to deal with that. Cheap Arduino Nano clones may need the `AtMega3288P (Old Bootloader)` processor setting in the Arduino IDE, otherwise flashing will fail.

* Remove the middle jumper (CFG2) from each stepper on the CNC shield to set the TMC2100 to 1/16th microstepping at spreadCycle

* `config.h` needs to be replaced by the provided file to restrict the homing sequence to X axis (sensor on carriage) only

* EEPROM settings for grbl are listed in `grblsettings.txt`

* set the voltages for the NEMA8 motor to 0.2A (TMC2208 should be set to 0.3V at the VREF pin). More info: [watterott](https://learn.watterott.com/silentstepstick/faq/)

# configuring Raspberry Pi OS

* enable camera using `sudo raspi-config`

* disable the red LED on v1 camera boards by adding `disable_camera_led=1` at the end of `/boot/config.txt`

* install python: `sudo apt-get update && sudo apt-get install -y python3-pip`

* install the requirements: `pip3 install -r requirements.txt`
