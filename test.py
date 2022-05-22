from PIL import Image, ImageDraw
import math

DIAMETER        = 1000
SENSOR_SIZE     = [3.6 * 10, 2.7 * 10]

IMAGE_SIZE      = [1100, 1100]

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

    print(points)

    points = [rotate_point(xy, angle) for xy in points] # ignore center here
    points = [(xy[0] + center[0], xy[1] + center[1]) for xy in points]

    return points

def get_positions(diameter, sensor_size):

    # calculate min number of rings without gaps (ceil will introduce necessary overlap)
    # ring0 is always at center, so subtract half a sensor size
    num_rings = math.ceil((diameter-sensor_size[1])/2/sensor_size[1])
    ring_offsets = [x * sensor_size[1] for x in range(0, num_rings)]
    positions_per_ring = []

    for offset in ring_offsets:
        if offset == 0:
            positions_per_ring.append([[0, 0]])
            continue

        circ = 2 * math.pi * offset
        num_stops = math.ceil(circ/sensor_size[0])

        stops = []
        for i in range(0, num_stops):
            stops.append([offset, (i/num_stops) * 360]) # degree

        positions_per_ring.append(stops)

    return positions_per_ring

positions_per_ring = get_positions(DIAMETER, SENSOR_SIZE)
for ring in positions_per_ring:
    print("pos: {} stops: {}".format(ring[0][0], len(ring)))

with Image.new(mode="RGB", size=IMAGE_SIZE) as im:
    draw = ImageDraw.Draw(im, "RGBA")
    draw.rectangle((0, 0, *IMAGE_SIZE), fill=(0, 0, 0))

    for ring in positions_per_ring:

        center = [IMAGE_SIZE[0]/2, IMAGE_SIZE[1]/2]

        x_coord = ring[0][0]
        draw.ellipse(
            (center[0]-x_coord, center[1]-x_coord, 
            center[0]+x_coord, center[1]+x_coord), 
            outline=(255, 255, 255, 10), width=2)

        # for pos in ring:
        #     x_coord_rel = pos[0]
        #     radius      = x_coord_rel
        #     x_coord_abs = (center[0] + x_coord_rel, center[1])
        #     y_coord_deg = pos[1]
        #     y_coord_abs = [center[0] + radius * math.cos(math.radians(y_coord_deg)), center[1] + radius * math.sin(math.radians(y_coord_deg))]
        #     draw.ellipse(
        #         (y_coord_abs[0]-SENSOR_SIZE/2, y_coord_abs[1]-SENSOR_SIZE/2, 
        #         y_coord_abs[0]+SENSOR_SIZE/2, y_coord_abs[1]+SENSOR_SIZE/2), 
        #         outline=(100, 100, 100), width=2)

        for pos in ring:
            rot_points = get_rotated_sensor(pos[0], pos[1], SENSOR_SIZE, center=center)

            print(rot_points)
            draw.polygon(rot_points, fill=(255, 255, 255, 90), outline=(255, 255, 255, 125))

    # print("foo")
    # rot_points = get_rotated_sensor(50, 45, [SENSOR_SIZE, SENSOR_SIZE], center=[IMAGE_SIZE[0]/2, IMAGE_SIZE[1]/2])
    # print(rot_points)
    # draw.polygon(rot_points, outline=(255, 0, 0))


    im.save("output.png", "PNG")


