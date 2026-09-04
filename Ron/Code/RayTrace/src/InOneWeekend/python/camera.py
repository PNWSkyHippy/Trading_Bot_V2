# Python port of camera.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math
import sys
from color import Color, write_color
from hittable import HitRecord
from interval import Interval
from ray import Ray
from rtweekend import degrees_to_radians, infinity, random_double
from vec3 import Point3, Vec3, cross, random_in_unit_disk, unit_vector
from PIL import Image
import io

class Camera:
    def __init__(self):
        self.outfile = None
        self.printout = False
        self.aspect_ratio = 1.0  # Ratio of image width over height
        self.image_width = 100  # Rendered image width in pixel count
        self.samples_per_pixel = 10  # Count of random samples for each pixel
        self.max_depth = 10  # Maximum number of ray bounces into scene

        self.vfov = 90  # Vertical view angle (field of view)
        self.lookfrom = Point3(0, 0, 0)  # Point camera is looking from
        self.lookat = Point3(0, 0, -1)  # Point camera is looking at
        self.vup = Vec3(0, 1, 0)  # Camera-relative "up" direction

        self.defocus_angle = 0  # Variation angle of rays through each pixel
        self.focus_dist = 10  # Distance from camera lookfrom point to plane of perfect focus

        self.image_height = 0
        self.pixel_samples_scale = 1.0 / self.samples_per_pixel
        self.center = Point3()
        self.pixel00_loc = Point3()
        self.pixel_delta_u = Vec3()
        self.pixel_delta_v = Vec3()
        self.u = Vec3()
        self.v = Vec3()
        self.w = Vec3()
        self.defocus_disk_u = Vec3()
        self.defocus_disk_v = Vec3()

    def render(self, world):
        self.initialize()
        if self.printout:
            sys.stdout.write(f"P3\n{self.image_width} {self.image_height}\n255\n")
        ppm_image = f'P3\n{self.image_width} {self.image_height}\n255\n'
        for j in range(self.image_height):
            remaining = self.image_height - j
            sys.stderr.write(f"\rScanlines remaining: {remaining} ")
            sys.stderr.flush()
            row_rgb = ""
            for i in range(self.image_width):
                pixel_color = Color(0, 0, 0)
                for _sample in range(self.samples_per_pixel):
                    r = self.get_ray(i, j)
                    pixel_color += self.ray_color(r, self.max_depth, world)
                    ir = int(255.999 * (self.pixel_samples_scale  * pixel_color.x()))
                    ig = int(255.999 * (self.pixel_samples_scale  * pixel_color.y()))
                    ib = int(255.999 * (self.pixel_samples_scale * pixel_color.z()))
                    row_rgb += f'{ir} {ig} {ib}\t\t'
                    ir, ig, ib = (0,0,0)
                ppm_image += f'{row_rgb}\n' 
                if self.printout:
                    write_color(sys.stdout, self.pixel_samples_scale * pixel_color)
        if self.outfile is not None:
            self.write_file(ppm_image)
        sys.stderr.write("\rDone.                 \n")

    def write_file(self,img):
        ppm_bytes = img.encode('utf-8') if isinstance(img, str) else img
        # 2. Wrap the buffer in an in-memory stream
        ppm_stream = io.BytesIO(ppm_bytes)
        self.outfile = self.outfile if self.outfile else "default.ppm"
        try:
            # 3. Open it from memory and save it natively
            with Image.open(ppm_stream) as img:
                img = img.resize((1200, 1200))
                img.save(self.outfile, optimize=True)
                # Automatically converts and saves to disk
        except:
            raise ValueError("Error saving output file")
        im = Image.open(self.outfile)
        im.show()
            
    def initialize(self):
        self.image_height = int(self.image_width / self.aspect_ratio)
        self.image_height = 1 if self.image_height < 1 else self.image_height

        self.pixel_samples_scale = 1.0 / self.samples_per_pixel

        self.center = self.lookfrom

        # Determine viewport dimensions.
        theta = degrees_to_radians(self.vfov)
        h = math.tan(theta / 2)
        viewport_height = 2 * h * self.focus_dist
        viewport_width = viewport_height * (self.image_width / self.image_height)

        # Calculate the u,v,w unit basis vectors for the camera coordinate frame.
        self.w = unit_vector(self.lookfrom - self.lookat)
        self.u = unit_vector(cross(self.vup, self.w))
        self.v = cross(self.w, self.u)

        # Calculate the vectors across the horizontal and down the vertical viewport edges.
        viewport_u = viewport_width * self.u
        viewport_v = viewport_height * -self.v

        # Calculate the horizontal and vertical delta vectors from pixel to pixel.
        self.pixel_delta_u = viewport_u / self.image_width
        self.pixel_delta_v = viewport_v / self.image_height

        # Calculate the location of the upper left pixel.
        viewport_upper_left = (
            self.center - (self.focus_dist * self.w) - viewport_u / 2 - viewport_v / 2
        )
        self.pixel00_loc = viewport_upper_left + 0.5 * (self.pixel_delta_u + self.pixel_delta_v)

        # Calculate the camera defocus disk basis vectors.
        defocus_radius = self.focus_dist * math.tan(degrees_to_radians(self.defocus_angle / 2))
        self.defocus_disk_u = self.u * defocus_radius
        self.defocus_disk_v = self.v * defocus_radius

    def get_ray(self, i, j):
        # Construct a camera ray originating from the defocus disk and directed at a randomly
        # sampled point around the pixel location i, j.

        offset = self.sample_square()
        pixel_sample = (
            self.pixel00_loc
            + ((i + offset.x()) * self.pixel_delta_u)
            + ((j + offset.y()) * self.pixel_delta_v)
        )

        ray_origin = self.center if self.defocus_angle <= 0 else self.defocus_disk_sample()
        ray_direction = pixel_sample - ray_origin

        return Ray(ray_origin, ray_direction)

    def sample_square(self):
        # Returns the vector to a random point in the [-.5,-.5]-[+.5,+.5] unit square.
        return Vec3(random_double() - 0.5, random_double() - 0.5, 0)

    def sample_disk(self, radius):
        # Returns a random point in the unit (radius 0.5) disk centered at the origin.
        return radius * random_in_unit_disk()

    def defocus_disk_sample(self):
        # Returns a random point in the camera defocus disk.
        p = random_in_unit_disk()
        return self.center + (p[0] * self.defocus_disk_u) + (p[1] * self.defocus_disk_v)

    def ray_color(self, r, depth, world):
        # If we've exceeded the ray bounce limit, no more light is gathered.
        if depth <= 0:
            return Color(0, 0, 0)

        rec = HitRecord()

        if world.hit(r, Interval(0.001, infinity), rec):
            scattered = rec.mat.scatter(r, rec)
            if scattered is not None:
                attenuation, scattered_ray = scattered
                return attenuation * self.ray_color(scattered_ray, depth - 1, world)
            return Color(0, 0, 0)

        unit_direction = unit_vector(r.direction())
        a = 0.5 * (unit_direction.y() + 1.0)
        return (1.0 - a) * Color(1.0, 1.0, 1.0) + a * Color(0.5, 0.7, 1.0)
