#!/bin/python3

import logging
import argparse
from datetime import datetime
import math
import time
import os
import subprocess
import shutil
import re
import sys
from fractions import Fraction

import serial
import picamera

SCANCAM_ENDSTOP_DIST    = 37.70
SCANCAM_DIAMETER        = 60
SCANCAM_SENSOR_SIZE     = [3.6, 2.7]

SERIAL_BAUDRATE         = 115200
SERIAL_TIMEOUT_READ     = 0.5
SERIAL_TIMEOUT_WRITE    = 0.5
SERIAL_PORT_GRBL        = ["/dev/ttyUSB0", "/dev/tty.wchusbserial14210", "/dev/tty.usbserial-14420"]
SERIAL_PORT_TRIGGER     = "/dev/ttyAMA0"

FILE_EXTENSION          = ".jpg"
OUTPUT_DIRECTORY        = "/home/pi/storage"

FEEDRATE                = 400 

FEEDRATE_X              = 150
FEEDRATE_Y              = 500

# INTERVAL MODE
PRE_CAPTURE_WAIT        = 0.5
POST_CAPTURE_WAIT       = 0.1

MODE_STILL              = "still"
MODE_VIDEO              = "video"
MODE_MOVE               = "move"        
MODE_WAIT               = "wait"
MODE_CALIBRATE          = "calibrate" # move to center and rotate
MODE_DISABLE            = "disable"

# PICAMERA

SENSOR_MODE             = 0
EXPOSURE_COMPENSATION   = 0

def get_status(ser):
    ret = _send_command(ser, "?")

    # example: <Idle|MPos:17.530,0.000,0.000|FS:0,0|WCO:0.000,0.000,0.000>\r\nok\r
    ret = ret[ret.index("<")+1:ret.index(">")]
    return ret.split("|")[0].upper()


def _send_command(ser, cmd, param=None, ignore_empty=False):
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
        # response = re.sub("[^a-zA-Z0-9_ .$]", '', response)

        log.debug("serial receive: {}".format(response))

        if response is None or len(response) == 0:
            log.debug("empty response".format())

            if ignore_empty:
                return None
            else:
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
        raise se

    except Exception as e:
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
            resp = get_status(ser_grbl)
            if resp == "IDLE":
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

    time.sleep(5)

    # camera.exposure_mode = "off"
    # camera.awb_mode = "off"
    camera.awb_mode = "sunlight"


def close_ports():

    log.info("closing serial connections")

    if not ser_grbl is None:
        ser_grbl.close()

    if not ser_trigger is None:
        ser_trigger.close()

    if not camera is None:
        camera.stop_preview()
        camera.close()


def get_positions(diameter, sensor_size):

    # calculate min number of rings without gaps (ceil will introduce necessary overlap)
    # ring0 is always at center, so subtract half a sensor size
    num_rings = math.ceil((diameter-sensor_size[1])/2/sensor_size[1])
    ring_offsets = [x * sensor_size[1] for x in range(0, num_rings)]
    positions_per_ring = []

    for i in range(0, len(ring_offsets)):
        offset = ring_offsets[i]

        if offset == 0:
            positions_per_ring.append([[0, 0]])
            continue

        # when computing the circumference do not use the center of the sensor
        # but the middle of the top border of the sensor (to avoid gaps)
        circ = 2 * math.pi * (offset + sensor_size[1]/2)
        num_stops = math.ceil(circ/sensor_size[0])

        stops = []
        for j in range(0, num_stops):
            stops.append([offset, (j/num_stops) * 360]) # degree

        # traverse backwards in every second ring
        if i % 2 == 0:
            positions_per_ring.append(stops)
        else:
            positions_per_ring.append(list(reversed(stops)))

    return positions_per_ring


log = logging.getLogger()

if __name__ == "__main__":

    global ser_grbl
    global ser_trigger
    global camera

    ap = argparse.ArgumentParser()

    ap.add_argument(
        "command",
        default=MODE_STILL,
        choices=[MODE_STILL, MODE_VIDEO, MODE_MOVE, MODE_CALIBRATE, MODE_WAIT, MODE_DISABLE], 
        help=""
    )

    ap.add_argument("-x", type=float, default=0, help="X axis units [mm]")
    ap.add_argument("-y", type=float, default=0, help="Y axis units [mm]")
    ap.add_argument("-f", "--feedrate", type=int, default=FEEDRATE, help="movement speed [mm/min]")
    ap.add_argument("-d", "--delay", type=int, default=1, help="delay [s]")
    ap.add_argument("--no-camera", action="store_true", default=False, help="do not initialize picamera")
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

    # sanity checks

    if SCANCAM_DIAMETER > (SCANCAM_ENDSTOP_DIST * 2 - 2.0):
        log.error("SCANCAM_DIAMETER is {}, which is larger than 2x SCANCAM_ENDSTOP_DIST ({}). exiting.".format(SCANCAM_DIAMETER, SCANCAM_ENDSTOP_DIST*2))
        sys.exit(-1)

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

    time.sleep(1.0)
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

    # GRBL setup

    # start homing
    try:
        log.info("starting homing")
        _send_command(ser_grbl, "$H", ignore_empty=True)
        wait_for_idle()

        # check for problems during homing. 
        # resp = _send_command(ser_grbl, "$")
        # log.info("grbl: {}".format(resp))

        time.sleep(0.5)

        status = get_status(ser_grbl)

        if len(status) == 0: # if empty, repeat
            status = get_status(ser_grbl)            

        if status != "IDLE":
            raise Exception("non IDLE status: {}".format(status))
        else:
            log.info("homing successful")

    except Exception as e:
        log.error("homing failed: {}".format(e))
        sys.exit(-1)
    
    grbl_setup_commands = [
        "G90",                                          # absolute positioning
        "G10 P0 L20 X0 Y0 Z0",                          # set offsets to zero
        "G21",                                          # set units to millimeters
        "G1 F{}".format(FEEDRATE),                      # set feedrate to _ mm/min
        "G92 X{} Y0 Z0".format(SCANCAM_ENDSTOP_DIST),   # set work position
        "G1 X0 F{}".format(FEEDRATE_X),                 # move to center
        "G1 Y0 F{}".format(FEEDRATE_Y)                  # move to center
    ]

    for cmd in grbl_setup_commands:
        try:
            resp = _send_command(ser_grbl, cmd)
        except Exception as e:
            log.error("initializing grbl failed with cmd \"{}\": {}".format(cmd, e))
            sys.exit(-1)

    wait_for_idle()

    log.info("initialized and centered")

    # once the carriage is homes, initalize picamera

    if not args["no_camera"]:
        init_picamera()

    # modes

    if args["command"] == MODE_STILL: 

        log.info("STILL MODE")

        positions = get_positions(
            SCANCAM_DIAMETER, 
            [SCANCAM_SENSOR_SIZE[0]-0.1, SCANCAM_SENSOR_SIZE[1]-0.1] # create a bit of overlap
        )

        # debug pattern
        # positions = [[[0, 0]]]
        # for i in range(1, 10):
        #     positions.append([
        #         [1*i, 0],        
        #         [1*i, 90],
        #         [1*i, 180],
        #         [1*i, 270],
        #     ])

        total_pos = sum([len(x) for x in positions])
        num_pos = 0

        # cmd = "G1 X{} Y{} F{}".format(0, 0, FEEDRATE_SLOW*2)
        # _send_command(ser_grbl, cmd)
        # wait_for_idle()
        # close_ports()
        # sys.exit(0)

        for i in range(0, len(positions)):

            ring = positions[i]

            for j in range(0, len(ring)):

                pos = ring[j]
                num_pos += 1

                log.info("POS {}/{} | R: {}/{} I:{}/{} ".format(
                    num_pos, total_pos, 
                    i, len(positions), 
                    j, len(ring)
                ))

                # separate movement commands for X and Y so we can have different feedrates

                cmd = "G1 X{} F{}".format(ring[j][0], FEEDRATE_X)
                _send_command(ser_grbl, cmd)

                wait_for_idle()

                cmd = "G1 Y{} F{}".format(ring[j][1], FEEDRATE_Y)
                _send_command(ser_grbl, cmd)

                wait_for_idle()

                log.debug("TRIGGER [{}/{}]".format(num_pos, total_pos))

                time.sleep(PRE_CAPTURE_WAIT)

                filename = [OUTPUT_DIRECTORY, "{:05}-{:05}-{:05}_{:06.3f}_{:06.3f}{}".format(
                    num_pos, i, j,
                    ring[j][0], ring[j][1],
                    FILE_EXTENSION
                )]

                if filename is None:
                    raise Exception("could not acquire filename")

                camera.capture(os.path.join(*filename))

                log.debug("FILE: {}".format(filename[1]))

                time.sleep(POST_CAPTURE_WAIT)

        # return to home

        log.info("return home")

        cmd = "G1 X{} Y{}".format(0, 0)
        _send_command(ser_grbl, cmd)

        wait_for_idle()

        log.info("DONE")

    elif args["command"] == MODE_CALIBRATE: 

        log.info("CALIBRATE MODE")

        positions = [
            [0, 0],
            [0, 22.5],
            [0, 45],
            [0, 67.5],
            [0, 90],
            [0, 112.5],
            [0, 135],
            [0, 157.5],
            [0, 180]
        ]

        for i in range(0, len(positions)):

            log.info("POS {}/{}".format(i, len(positions)))

            pos = positions[i]

            cmd = "G1 X{} F{}".format(pos[0], FEEDRATE_X)
            _send_command(ser_grbl, cmd)

            wait_for_idle()

            cmd = "G1 Y{} F{}".format(pos[1], FEEDRATE_Y)
            _send_command(ser_grbl, cmd)

            wait_for_idle()

            log.debug("TRIGGER [{}/{}]".format(i, len(positions)))

            time.sleep(PRE_CAPTURE_WAIT)

            filename = [OUTPUT_DIRECTORY, "calibrate_{:06.2f}_{:05}_{:06.3f}_{:06.3f}{}".format(
                SCANCAM_ENDSTOP_DIST,
                i,
                pos[0], pos[1],
                FILE_EXTENSION
            )]

            if filename is None:
                raise Exception("could not acquire filename")

            camera.capture(os.path.join(*filename))

            log.debug("FILE: {}".format(filename[1]))

            time.sleep(POST_CAPTURE_WAIT)

        # return to home

        log.info("return home")

        cmd = "G1 X{} Y{}".format(0, 0)
        _send_command(ser_grbl, cmd)

        wait_for_idle()

        log.info("DONE")

    elif args["command"] == MODE_MOVE:

        pos = [float(args["x"]), float(args["y"])]
        log.info("MOVE | X: {:5.2f} Y:{:5.2f}".format(*pos))

        cmd = "G1 X{} Y{} F{}".format(*pos, FEEDRATE)
        _send_command(ser_grbl, cmd)

        wait_for_idle()

        log.info("DONE")

    elif args["command"] == MODE_WAIT:

        log.info("WAIT")

        time.sleep(10)

        close_ports()

        log.info("DONE")

    elif args["command"] == MODE_VIDEO:

        pos = [float(args["x"]), float(args["y"])]
        log.info("VIDEO | X: {:5.2f} Y:{:5.2f} F:{}".format(*pos, args["feedrate"]))

        cmd = "G1 "

        if not args["x"] is None:
            cmd += "X{}".format(args["x"])

        if not args["y"] is None:
            cmd += "Y{}".format(args["y"])

        cmd += " F{}".format(args["feedrate"]) 
        
        _send_command(ser_grbl, cmd)

        wait_for_idle()

        log.info("DONE")

    elif args["command"] == MODE_BOUNCE:

        pos = [float(args["x"]), float(args["y"])]
        log.info("BOUNCE | X: {:5.2f} Y:{:5.2f} F: {}".format(*pos, args["feedrate"]))

        move_cmd = "G1 "

        if not args["x"] is None:
            move_cmd += "X{}".format(args["x"])

        if not args["y"] is None:
            move_cmd += "Y{}".format(args["y"])

        move_cmd += " F{}".format(args["feedrate"]) 

        cmds = [move_cmd, "G1 X0 Y0 F{}".format(args["feedrate"])]
        
        for cmd in cmds:
            _send_command(ser_grbl, cmd)
            wait_for_idle()

        log.info("DONE")

    else:
        raise Exception("unknown mode: {}".format(args["command"]))

    close_ports()
    log.info("done.")