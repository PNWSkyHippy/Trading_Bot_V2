from vectors import Vec3, Point3, dot, cross, unit_vector
from colors import write_color, Color
import rays
import logging
import sys, io
from PIL import Image
from math import sqrt

logger = logging.getLogger(__name__)

aspect_ratio = 16.0 / 9.0
image_width = 400

# Calculate the image height, and ensure that it's at least 1.
image_height = int(image_width / aspect_ratio)
if image_height < 1: 
    image_height = 1


# Viewport widths less than one are ok since they are real valued.
viewport_height = 2.0;
viewport_width = viewport_height * (float(image_width)/image_height)

"""
    Camera center (The EYE) is 0,0,0
    Orientation Y is up, X to the right, negative z straight ahead
    also called right hand coordinates
    The screen were projcting onto hhs Y 0 top left (inverted)
   
 |--------------------------------> Vx
 |  Q       P0,0   Du    
 |   --------|-----|-|---------------  Q - ViewPort upper left
 |   | . . . v . . ._. . . . . . . .   P0,0 - a pixel location
 |   | . . . o . . o o . . . . . . .   Vx  ViewPort Vector along X
 | D |- o . . . . . . . . . . . . .    Vy  ViewPort Vector along Y
 | y |- o . . . . . . . . . . . . .    Du  Pixe; Delta
 |   | . . . . . . . . . . . . . . .   Dv  Pixel Delta
     | . . . . . . . . . . . . . . .
"""

"""
def ray_color(r):
    "" r is a Ray ""
    if (hit_sphere(Point3(0,0,-1), 0.5, r)):
        return Color(1, 0, 0)
    col1 = Color(1.0, 1.0, 1.0)#   
    col2 = Color(0.5, 0.7, 1.0)
    unit_direction = unit_vector(r.direction())
    a = 0.5 * (unit_direction.y() + 1.0)
    return (1.0 - a) * col1 + a * col2
"""

#def ray_color(r):
#    col1 = Color(1.0,1.0,1.0)
#    col2 = Color(0.5, 0.7, 1.0)
#    unit_direction = unit_vector(r.direction())#   
#    a = 0.5 * (unit_direction.y() + 1.0)
#    return (1.0 - a) * col1 + a * col2


def main():
    # Camera
    
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(levelname)s: %(message)s"
    )
    
    focal_length = 1.0
    viewport_height = 2.0
    viewport_width = viewport_height * (float(image_width)/image_height)
    camera_center = Point3(0, 0, 0)

    # Calculate the vectors across the horizontal and down the vertical viewport edges.
    viewport_u = Vec3(viewport_width, 0, 0)
    viewport_v = Vec3(0, -viewport_height, 0)

    # Calculate the horizontal and vertical delta vectors from pixel to pixel.
    pixel_delta_u = viewport_u / image_width
    pixel_delta_v = viewport_v / image_height

    # Calculate the location of the upper left pixel.
    viewport_upper_left = camera_center - Vec3(0, 0, focal_length) - viewport_u / 2 - viewport_v / 2
    pixel00_loc = viewport_upper_left + 0.5 * (pixel_delta_u + pixel_delta_v)
#    print(f'P3\n{image_width} {image_height}\n255\n')
    ppm_img = f'P3\n{image_width} {image_height}\n255\n'
#    ray_colors = Color.value()
    for j in range(0,image_height):
        logger.debug(f'\rScanlines remaining: {image_height - j} ')
        row_rgb = ""
        for i in range(0,image_width):
            pixel_center = pixel00_loc + (i * pixel_delta_u) + (j * pixel_delta_v)
            ray_direction = pixel_center - camera_center
            r = Ray(camera_center, ray_direction)

            pixel_color = ray_color(r)
            r = pixel_color.x()
            g = pixel_color.y()
            b = pixel_color.z()

            ir = int(255.999 * r)
            ig = int(255.999 * g)
            ib = int(255.999 * b)
            row_rgb += f'{ir} {ig} {ib}\t\t'
 #           write_color(pixel_color)
        ppm_img += f'{row_rgb}\n' 
    logger.debug('\rDone')
    # 1. Convert your string buffer to bytes (if it isn't already bytes)
    ppm_bytes = ppm_img.encode('utf-8') if isinstance(ppm_img, str) else ppm_img
    # 2. Wrap the buffer in an in-memory stream
    ppm_stream = io.BytesIO(ppm_bytes)
    outfile = "mytest.ppm"
##    outfile = outfile if outfile else "mytest.ppm"
    try:
        # 3. Open it from memory and save it natively
        with Image.open(ppm_stream) as img:
            img.save(outfile, optimize=True)
            # Automatically converts and saves to disk
    except:
        raise ValueError("Error saving output file")
    im = Image.open(outfile)
    im.show()

    
    
    
    
    
if __name__ == "__main__":
    main()