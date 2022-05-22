#!/bin/python3

import logging
import argparse
from datetime import datetime
import time
import os
import subprocess
import shutil
import re
import sys
from fractions import Fraction

import serial
import picamera

SCANCAM_DIAMETER        = 100 # exact diameter at endstop position

SERIAL_BAUDRATE         = 115200
SERIAL_TIMEOUT_READ     = 0.5
SERIAL_TIMEOUT_WRITE    = 0.5
SERIAL_PORT_GRBL        = ["/dev/tty.wchusbserial14210", "/dev/ttyUSB0", "/dev/tty.usbserial-14420"]
SERIAL_PORT_TRIGGER     = "/dev/ttyAMA0"

FILE_EXTENSION          = ".jpg"
OUTPUT_DIRECTORY        = "/home/pi/storage"

FEEDRATE                = 2000 
FEEDRATE_SLOW           = 500

# INTERVAL MODE
PRE_CAPTURE_WAIT        = 0.5
POST_CAPTURE_WAIT       = 0.1

MODE_STILL              = "still"
MODE_VIDEO              = "video"
MODE_BOUNCE             = "bounce"
MODE_MOVE               = "move"
MODE_WAIT               = "wait"
MODE_DISABLE            = "disable"

# PICAMERA

SENSOR_MODE             = 0
EXPOSURE_COMPENSATION   = 0

def _send_command(ser, cmd, param=None):
    response = ""

    try:
        full_cmd = None
        if param is None:
            full_cmd = cmd
        else:
            full_cmd = "{} {}".format(cmd, param)

        log.debug("serial send: {}".format(full_cmd))

        ser.write(bytearray(full_cmd, "utf-8"))
        ser.write(bytearray("\n", "utf-8"))

        response = ser.read(100)
        response = response.decode("utf-8") 

        # remove every non-alphanumeric / non-underscore / non-space / non-decimalpoint / non-dollarsign character
        response = re.sub("[^a-zA-Z0-9_ .$]", '', response)

        log.debug("serial receive: {}".format(response))

        if response is None or len(response) == 0:
            log.debug("empty response".format())
            raise Exception("empty response or timeout")

        if cmd == "?":
            return response

        if response.startswith(cmd):
            response = response[len(cmd):]

        if response.startswith("ok"):        
            if len(response) > 1:
                return response[3:]
            else: 
                return None
        else:
            log.debug("serial error, non ok response: {}".format(response))
            raise Exception("serial error, non ok response: {}".format(response))

    except serial.serialutil.SerialException as se:
        log.error("comm failed, SerialException: {}".format(se))
        raise se

    except Exception as e:
        log.error("comm failed, unknown exception: {}".format(e))
        raise e


def _acquire_filename(path):
    filename = None

    for i in range(0, 9999):
        name = i
        name = str(name).zfill(4)
        testname = name + FILE_EXTENSION
        if not os.path.exists(os.path.join(path, testname)):
            filename = testname
            break

    log.debug("acquired filename: {}".format(filename))

    return (path, filename)


def global_except_hook(exctype, value, traceback):
    close_ports()
    sys.__excepthook__(exctype, value, traceback)


# wait till grbl finished it's moves and reports status IDLE instead of RUN or ERROR
def wait_for_idle():
    while(True):
        try:
            # example: <Idle|MPos:17.530,0.000,0.000|FS:0,0|WCO:0.000,0.000,0.000>
            resp = _send_command(ser_grbl, "?")

            if resp.startswith("Idle"):
                break
        except Exception as e:
            log.debug("wait-for-idle loop failed: {}".format(e))
 

def init_picamera():

    global camera

    camera = picamera.PiCamera(sensor_mode=SENSOR_MODE) 
    camera.meter_mode = "average"
    camera.exposure_compensation = EXPOSURE_COMPENSATION

    resolutions = {}
    resolutions["HQ"] = [[4056, 3040], Fraction(1, 2)]
    resolutions["V2"] = [[3280, 2464], Fraction(1, 2)]
    resolutions["V1"] = [[2592, 1944], Fraction(1, 2)]

    for key in resolutions.keys():
        try:
            camera.resolution = resolutions[key][0]
            # camera.framerate = resolutions[key][1]
            camera_type = key
            log.info("camera resolution set to [{}]: {}".format(key, resolutions[key][0]))
            break
        except picamera.exc.PiCameraValueError as e:
            log.debug("failing setting camera resolution for {}, attempting fallback".format(key))

    camera.start_preview()

    time.sleep(3)

    camera.exposure_mode = "off"


def close_ports():

    log.info("closing serial connections")

    if not ser_grbl is None:
        ser_grbl.close()

    if not ser_trigger is None:
        ser_trigger.close()

    if not camera is None:
        camera.stop_preview()
        camera.close()


log = logging.getLogger()

if __name__ == "__main__":

    global ser_grbl
    global ser_trigger
    global camera

    ap = argparse.ArgumentParser()

    ap.add_argument(
        "command",
        default=MODE_STILL,
        choices=[MODE_STILL, MODE_VIDEO, MODE_BOUNCE, MODE_MOVE, MODE_WAIT, MODE_DISABLE], 
        help=""
    )

    ap.add_argument("-x", type=float, default=0, help="X axis units [mm]")
    ap.add_argument("-y", type=float, default=0, help="Y axis units [mm]")
    ap.add_argument("-f", "--feedrate", type=int, default=FEEDRATE, help="movement speed [mm/min]")
    ap.add_argument("-d", "--delay", type=int, default=1, help="delay [s]")
    ap.add_argument("--debug", action="store_true", default=False, help="print debug messages")
    args = vars(ap.parse_args())

    input_delay = args["delay"]

    log.info("init")

    # create logger
    log.handlers = [] # remove externally inserted handlers (systemd?)
    if args["debug"]:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter("%(asctime)s | %(name)-7s | %(levelname)-7s | %(message)s")

    # console handler and set level to debug
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)
    consoleHandler.setFormatter(formatter)
    log.addHandler(consoleHandler)

    # global exception hook for killing the serial connection
    sys.excepthook = global_except_hook

    camera = None
    ser_grbl = None
    ser_trigger = None

    for port_name in SERIAL_PORT_GRBL:
        try:
            ser_grbl = serial.Serial(
                port_name, SERIAL_BAUDRATE, 
                timeout=SERIAL_TIMEOUT_READ, 
                write_timeout=SERIAL_TIMEOUT_WRITE)

            log.debug("opening port {} successful".format(port_name))
            break
        except Exception as e:
            log.debug("opening port {} failed: {}".format(port_name, e))

    if ser_grbl is None:
        log.error("no grbl found on all ports. exit.")
        sys.exit(-1)

    time.sleep(2.0)
    response = ser_grbl.read(100) # get rid of init message "Grbl 1.1h ['$' for help]"

    if args["command"] == MODE_DISABLE:
        log.info("disabling motors...")
        resp = _send_command(ser_grbl, "$X")
        log.info("grbl: {}".format(resp))
        close_ports()
        log.info("motors disabled. exit...")
        sys.exit()

    if os.uname().nodename in ["raspberrypi", "slider"]:
        try:
            os.mkdir(OUTPUT_DIRECTORY)
        except OSError as e:
            log.debug("creating directory {} failed".format(OUTPUT_DIRECTORY))
    else:
        log.warn("platform is not raspberry pi ({}), not creating OUTPUT_DIRECTORY: {}".format(os.uname().nodename, OUTPUT_DIRECTORY))

    if not FILE_EXTENSION == ".jpg":
        log.warn("picamera mode enabled, overwriting FILE_EXTENSION to jpg")
        FILE_EXTENSION = ".jpg"

    init_picamera()

    # GRBL setup

    grbl_setup_commands = [
        # "G91",                      # relative positioning
        "G90",                      # absolute positioning
        "G10 P0 L20 X0 Y0 Z0",      # set current pos as zero
        "G21",                      # set units to millimeters
        "G1 F{}".format(FEEDRATE)   # set feedrate to _ mm/min
    ]

    for cmd in grbl_setup_commands:
        resp = _send_command(ser_grbl, cmd)

    # modes

    if args["command"] == MODE_STILL: 

        steps = []
        step_size = [0, 0, 0]

        

        if input_shutter <= 1:
            raise Exception("interval needs to be at least 2")

        if not args["x"] is None:
            step_size[0] = float(args["x"])/(input_shutter-1)

        if not args["y"] is None:
            step_size[1] = float(args["y"])/(input_shutter-1)

        for i in range(0, input_shutter+1):
            steps.append([step_size[0] * i, step_size[1] * i, step_size[2] * i])
        
        for i in range(0, input_shutter):

            log.info("INTERVAL {}/{} | X: {:5.2f} Y:{:5.2f} Z:{:5.2f}".format(
                i+1, input_shutter, *steps[i]))

            # move
            cmd = "G1 X{} Y{} Z{} F{}".format(*steps[i], FEEDRATE_SLOW)
            _send_command(ser_grbl, cmd)

            wait_for_idle()

            log.debug("TRIGGER [{}/{}]".format(i+1, input_shutter))

            # EXT SHUTTER:

            # # start timer
            # start = datetime.now()

            # # trigger
            # if ser_trigger is not None:
            #     pass
            # else:
            #     raise Exception("shutter not found")
 
            # # wait till timer ends
            # while (datetime.now() - (start + args["delay"])).total_seconds() < 0:
            #     time.sleep(0.1)
            #     print("sleep")

            # GPHOTO:

            time.sleep(PRE_CAPTURE_WAIT)

            temp_file = "capt0000{}".format(FILE_EXTENSION)
            filename = _acquire_filename(OUTPUT_DIRECTORY)

            if filename is None:
                raise Exception("could not acquire filename")

            if args["picamera"]:
                camera.capture(os.path.join(*filename))
            else:
                subprocess.run("gphoto2 --capture-image-and-download --force-overwrite", shell=True, check=True)
            
                if not os.path.exists(temp_file):
                    raise Exception("captured image file missing")
                shutil.move(temp_file, os.path.join(*filename))

            log.info("FILE: {}".format(filename[1]))

            time.sleep(POST_CAPTURE_WAIT)

        # return to home

        log.info("return home")

        cmd = "G1 X{} Y{} Z{}".format(0, 0, 0)
        _send_command(ser_grbl, cmd)

        wait_for_idle()

        log.info("DONE")

    elif args["command"] == MODE_MOVE:

        pos = [float(args["x"]), float(args["y"]), float(args["z"])]
        log.info("MOVE | X: {:5.2f} Y:{:5.2f} Z:{:5.2f}".format(*pos))

        cmd = "G1 X{} Y{} Z{} F{}".format(*pos, FEEDRATE)
        _send_command(ser_grbl, cmd)

        wait_for_idle()

        log.info("DONE")

    elif args["command"] == MODE_WAIT:

        log.info("WAIT")

        time.sleep(10)

        close_ports()

        log.info("DONE")

    elif args["command"] == MODE_VIDEO:

        pos = [float(args["x"]), float(args["y"]), float(args["z"])]
        log.info("VIDEO | X: {:5.2f} Y:{:5.2f} Z:{:5.2f} F: {}".format(*pos, args["feedrate"]))

        cmd = "G1 "

        if not args["x"] is None:
            cmd += "X{}".format(args["x"])

        if not args["y"] is None:
            cmd += "Y{}".format(args["y"])

        if not args["z"] is None:
            cmd += "Z{}".format(args["z"])

        cmd += " F{}".format(args["feedrate"]) 
        
        _send_command(ser_grbl, cmd)

        wait_for_idle()

        log.info("DONE")

    elif args["command"] == MODE_BOUNCE:

        pos = [float(args["x"]), float(args["y"]), float(args["z"])]
        log.info("BOUNCE | X: {:5.2f} Y:{:5.2f} Z:{:5.2f} F: {}".format(*pos, args["feedrate"]))

        move_cmd = "G1 "

        if not args["x"] is None:
            move_cmd += "X{}".format(args["x"])

        if not args["y"] is None:
            move_cmd += "Y{}".format(args["y"])

        if not args["z"] is None:
            move_cmd += "Z{}".format(args["z"])

        move_cmd += " F{}".format(args["feedrate"]) 

        cmds = [move_cmd, "G1 X0 Y0 Z0 F{}".format(args["feedrate"])]
        
        for cmd in cmds:
            _send_command(ser_grbl, cmd)
            wait_for_idle()

        log.info("DONE")

    else:
        raise Exception("unknown mode: {}".format(args["command"]))

    close_ports()
    log.info("done.")