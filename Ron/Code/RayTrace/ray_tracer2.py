from rtweekend import INFINITY
from  colors import Color
from  rays import Ray
from vectors import Vec3, unit_vector, Point3
from hittables import HitRecord
from hittable_lists import HittableList
from spheres import hit_sphere
import logging
import sys


logger = logging.getLogger(__name__)

def ray_color(r, world):
    rec = HitRecord()
    if (world.hit(r, 0, INFINITY, rec)):
        return 0.5 * (rec.normal + Color(1,1,1))

    unit_direction = unit_vector(r.direction())
    a = 0.5*(unit_direction.y() + 1.0)
    return (1.0-a) * Color(1.0, 1.0, 1.0) + a * Color(0.5, 0.7, 1.0)


def main():

#    // Image
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(levelname)s: %(message)s"
    )
    aspect_ratio = 16.0 / 9.0
    image_width = 400

    #// Calculate the image height, and ensure that it's at least 1.
    image_height = int(image_width / aspect_ratio)
    image_height = image_height if image_height >- 1 else 1

   # // World

    world = HittableList()

    world.add((Point3(0,0,-1), 0.5))
    world.add((Point3(0,-100.5,-1), 100))

 #   // Camera

    focal_length = 1.0
    viewport_height = 2.0
    viewport_width = viewport_height * (float(image_width)/image_height)
    camera_center = Point3(0, 0, 0)

#    // Calculate the vectors across the horizontal and down the vertical viewport edges.
    viewport_u = Vec3(viewport_width, 0, 0)
    viewport_v = Vec3(0, -viewport_height, 0)

#    // Calculate the horizontal and vertical delta vectors from pixel to pixel.
    pixel_delta_u = viewport_u / image_width
    pixel_delta_v = viewport_v / image_height

#    // Calculate the location of the upper left pixel.
    viewport_upper_left = camera_center - Vec3(0, 0, focal_length) - viewport_u/2 - viewport_v/2
    pixel00_loc = viewport_upper_left + 0.5 * (pixel_delta_u + pixel_delta_v)

 #   // Render

    logger.debug(f'"P3\n{image_width} {image_height}\n255\n')

    for j in range(0,image_height):
        logger.debug(f'\rScanlines remaining: {image_height - j}')
        for i in range(0,image_width):
            pixel_center = pixel00_loc + (i * pixel_delta_u) + (j * pixel_delta_v)
            ray_direction = pixel_center - camera_center
            r = Ray(camera_center, ray_direction)

            pixel_color = ray_color(r, world)
            write_color(sys.stdout,pixel_color)     
        logger.debug(f'\rDone.                 \n')
                      
if __name__ == "__main__":
    main()