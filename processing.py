import os
import math

from PIL import Image, ImageDraw
import cv2
import numpy as np

INPUT_DIR       = "input13"
OUTPUT_DIR      = "output"

SCALE_FACTOR    = 25

SHRINK_SENSOR   = 1.0

FLIP_HORIZONTAL = True
FLIP_VERTICAL   = True

DRAW_OUTLINE    = False

DIAMETER        = 100 * SCALE_FACTOR
SENSOR_SIZE     = [3.6 * SCALE_FACTOR * SHRINK_SENSOR, 2.7 * SCALE_FACTOR * SHRINK_SENSOR]
IMAGE_RES       = [2592, 1944]

IMAGE_SIZE      = [1100, 1100]

DIAM_OFFSET     = 0

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
        for f in filenames:

            if f.lower() == ".ds_store":
                continue

            files.append([dirpath, f])

    files = sorted(files)

    with Image.new(mode="RGB", size=IMAGE_SIZE) as output_image:
        draw = ImageDraw.Draw(output_image, "RGBA")
        draw.rectangle((0, 0, *IMAGE_SIZE), fill=(0, 0, 0))

        center = [IMAGE_SIZE[0]/2, IMAGE_SIZE[1]/2]

        img_out = np.array(output_image) 
        img_out = img_out[:, :, ::-1].copy() # RGB to BGR

        for i in range(0, len(files)):
            f = files[i]

            print("processing: {}".format(f[1]))

            # naming convention
            # filename = [OUTPUT_DIR, "{:05}-{:05}-{:05}_{:06.3f}_{:06.3f}{}".format(
            #     num_pos, i, j,
            #     ring[j][0], ring[j][1],
            #     FILE_EXTENSION
            # )]

            coords = os.path.splitext(f[1])[0].split("_")

            dist = (float(coords[1]) + DIAM_OFFSET) * SCALE_FACTOR
            rot = float(coords[2])

            img = cv2.imread(os.path.join(f[0], f[1]))

            # flip input image in both axes
            img = cv2.flip(img, -1)

            avg_color_per_row = np.average(img, axis=0)
            avg_color = np.average(avg_color_per_row, axis=0)

            rot_points = get_rotated_sensor(dist, rot, SENSOR_SIZE, center=center)

            # PIL polygon
            # draw.polygon(
            #     rot_points, 
            #     #fill=(int(avg_color[0]), int(avg_color[1]), int(avg_color[2]), int(255/2)), 
            #     outline=(255, 255, 255, 40))


            # compute the transformation

            pts_src = np.array([
                (0, 0),
                (IMAGE_RES[0], 0),
                (IMAGE_RES[0], IMAGE_RES[1]),
                (0, IMAGE_RES[1])
            ])

            h, status = cv2.findHomography(pts_src, np.array(rot_points))
            img_overlay = cv2.warpPerspective(img, h, (img_out.shape[1], img_out.shape[0]))

            cv2.fillConvexPoly(img_out, np.array(rot_points, np.int32), 0, cv2.LINE_AA)
            img_out = img_out + img_overlay
            
            if DRAW_OUTLINE:
                cv2.polylines(img_out, [np.array(rot_points, np.int32)], isClosed=True, color=(125, 125, 125), thickness=1, lineType=cv2.LINE_AA)

            # cv2.imwrite(os.path.join(OUTPUT_DIR, "{:05}_overlay.png".format(i)), img_overlay)
            cv2.imwrite(os.path.join(OUTPUT_DIR, "{:05}.png".format(i)), img_out)

            # img_overlay.save(os.path.join(OUTPUT_DIR, "{:05}_overlay.png".format(i)), "PNG")
            # output_image.save(os.path.join(OUTPUT_DIR, "{:05}.png".format(i)), "PNG")

        output_image.save("output.png", "PNG")

        img_gray = cv2.cvtColor(img_out, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(os.path.join(OUTPUT_DIR, "output.png"), img_gray)
