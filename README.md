# flashing GRBL

* The cheap "CNC engraver shield" is not pin-compatible to the standard CNC shield, the STEP and DIR pins for all three axes are switched. Overwrite `pin_map.h` to deal with that. Cheap Arduino Nano clones may need the `AtMega3288P (Old Bootloader)` processor setting in the Arduino IDE, otherwise flashing will fail.

* Remove the middle jumper (CFG2) from each stepper on the CNC shield to set the TMC2100 to 1/16th microstepping at spreadCycle

* `config.h` needs to be replaced by the provided file to restrict the homing sequence to X axis (sensor on carriage) only

* EEPROM settings for grbl are listed in `grblsettings.txt`