import os
import math

from PIL import Image, ImageDraw
# import cv2
# import numpy as np

INPUT_DIR       = "input"
OUTPUT_DIR      = "output"

SCALE_FACTOR    = 10

DIAMETER        = 100 * SCALE_FACTOR
SENSOR_SIZE     = [3.6 * SCALE_FACTOR, 2.7 * SCALE_FACTOR]

IMAGE_SIZE      = [1100, 1100]

files = []

def rotate_point(xy, angle, center=[0, 0]):

    s = math.sin(math.radians(angle))
    c = math.cos(math.radians(angle))

    x = (xy[0]-center[0]) * c - (xy[1]-center[1]) * s + center[0]
    y = (xy[0]-center[0]) * s + (xy[1]-center[1]) * c + center[1]

    return (x, y)

def get_rotated_sensor(offset, angle, sensor_size, center=[0, 0]):

    # order CW
    points = [
        [-sensor_size[0]/2, offset-sensor_size[1]/2],
        [+sensor_size[0]/2, offset-sensor_size[1]/2],
        [+sensor_size[0]/2, offset+sensor_size[1]/2],
        [-sensor_size[0]/2, offset+sensor_size[1]/2],
    ]

    points = [rotate_point(xy, angle) for xy in points] # ignore center here
    points = [(xy[0] + center[0], xy[1] + center[1]) for xy in points]

    return points

if __name__ == "__main__":

    for (dirpath, dirnames, filenames) in os.walk(INPUT_DIR):
        files.append(filenames)
        
    f = []
        
    f.append([0, 0])
    f.append([27.0, 0.0])
    f.append([27.0, 45.0])
    f.append([27.0, 90.0])
    f.append([27.0, 135.0])
    f.append([27.0, 180.0])
    f.append([27.0, 225.0])
    f.append([27.0, 270.0])
    f.append([27.0, 315.0])
    f.append([54.0, 0.0])
    f.append([54.0, 30.0])
    f.append([54.0, 60.0])
    f.append([54.0, 90.0])
    f.append([54.0, 120.0])
    f.append([54.0, 150.0])
    f.append([54.0, 180.0])
    f.append([54.0, 210.0])
    f.append([54.0, 240.0])
    f.append([54.0, 270.0])
    f.append([54.0, 300.0])
    f.append([54.0, 330.0])
    f.append([81.0, 0.0])
    f.append([81.0, 21.176470588235293])
    f.append([81.0, 42.35294117647059])
    f.append([81.0, 63.529411764705884])
    f.append([81.0, 84.70588235294117])
    f.append([81.0, 105.88235294117648])
    f.append([81.0, 127.05882352941177])
    f.append([81.0, 148.23529411764704])
    f.append([81.0, 169.41176470588235])
    f.append([81.0, 190.58823529411765])
    f.append([81.0, 211.76470588235296])
    f.append([81.0, 232.94117647058826])
    f.append([81.0, 254.11764705882354])
    f.append([81.0, 275.2941176470588])
    f.append([81.0, 296.4705882352941])
    f.append([81.0, 317.6470588235294])
    f.append([81.0, 338.8235294117647])
    f.append([108.0, 0.0])
    f.append([108.0, 16.363636363636363])
    f.append([108.0, 32.72727272727273])
    f.append([108.0, 49.090909090909086])
    f.append([108.0, 65.45454545454545])
    f.append([108.0, 81.81818181818181])
    f.append([486.0, 163.63636363636363])
    f.append([486.0, 167.72727272727272])
    f.append([486.0, 171.8181818181818])
    f.append([486.0, 175.9090909090909])
    f.append([486.0, 180.0])
    f.append([486.0, 184.0909090909091])
    f.append([486.0, 188.1818181818182])
    f.append([486.0, 192.27272727272725])
    f.append([486.0, 196.36363636363635])
    f.append([486.0, 200.45454545454544])
    f.append([486.0, 204.54545454545456])
    f.append([486.0, 208.63636363636365])
    f.append([486.0, 212.72727272727275])
    f.append([486.0, 216.8181818181818])
    f.append([486.0, 220.9090909090909])
    f.append([486.0, 225.0])
    f.append([486.0, 229.0909090909091])
    f.append([486.0, 233.1818181818182])
    f.append([486.0, 237.27272727272725])
    f.append([486.0, 241.36363636363635])
    f.append([486.0, 245.45454545454544])
    f.append([486.0, 249.54545454545456])
    f.append([486.0, 253.63636363636365])
    f.append([486.0, 257.72727272727275])
    f.append([486.0, 261.8181818181818])
    f.append([486.0, 265.90909090909093])
    f.append([486.0, 270.0])
    f.append([486.0, 274.09090909090907])
    f.append([486.0, 278.1818181818182])
    f.append([486.0, 282.27272727272725])
    f.append([486.0, 286.3636363636364])
    f.append([486.0, 290.45454545454544])
    f.append([486.0, 302.72727272727275])
    f.append([486.0, 306.8181818181818])
    f.append([486.0, 310.90909090909093])
    f.append([486.0, 315.0])
    f.append([486.0, 319.09090909090907])
    f.append([486.0, 323.1818181818182])
    f.append([486.0, 327.27272727272725])
    f.append([486.0, 331.3636363636364])
    f.append([486.0, 335.45454545454544])
    f.append([486.0, 339.54545454545456])
    files = f

    print(files)

    with Image.new(mode="RGB", size=IMAGE_SIZE) as output_image:
        draw = ImageDraw.Draw(output_image, "RGBA")
        draw.rectangle((0, 0, *IMAGE_SIZE), fill=(0, 0, 0))

        center = [IMAGE_SIZE[0]/2, IMAGE_SIZE[1]/2]

        for i in range(0, len(files)):
            f = files[i]

            # naming convention
            # filename = [OUTPUT_DIRECTORY, "{:05}-{:05}-{:05}_{:06.3f}_{:06.3f}{}".format(
            #     num_pos, i, j,
            #     ring[j][0], ring[j][1],
            #     FILE_EXTENSION
            # )]

            # coords = os.path.splitext(f)[0].split("_")

            # dist = float(coords[1])
            # rot = float(coords[2])

            # img = cv2.imread(f)
            # avg_color_per_row = np.average(img, axis=0)
            # avg_color = np.average(avg_color_per_row, axis=0)

            dist = f[0]
            rot = f[1]
            avg_color = [60, 120, 180]

            rot_points = get_rotated_sensor(dist, rot, SENSOR_SIZE, center=center)
            draw.polygon(rot_points, fill=(avg_color[0], avg_color[1], avg_color[2], int(255/2)), outline=(255, 255, 255, 40))

            output_image.save(os.path.join(OUTPUT_DIR, "{:05}.png".format(i)), "PNG")

        output_image.save("output.png", "PNG")