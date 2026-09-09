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
import sys, os
from color import Color, write_color
from hittable import HitRecord
from interval import Interval
from ray import Ray
from rtweekend import degrees_to_radians, infinity, random_double
from vec3 import Point3, Vec3, cross, random_in_unit_disk, unit_vector
from PIL import Image
import io, logging


logger = logging.getLogger(__name__)
from concurrent.futures import ProcessPoolExecutor
# Standalone worker function that runs in parallel on each CPU core

def render_single_scanline(args):
    j, image_width, samples_per_pixel, max_depth, pixel_samples_scale, cam_data, world = args
    
    # We unpack camera data to construct rays on the worker process
    row_rgb = []
    for i in range(image_width):
        pixel_color = Color(0, 0, 0)
        for _sample in range(samples_per_pixel):
            r = cam_data.get_ray(i, j)
            pixel_color += cam_data.ray_color(r, max_depth, world)
        scaled_color = pixel_samples_scale * pixel_color
        
        # Linear-to-gamma transform
        r_val = math.sqrt(scaled_color.x()) if scaled_color.x() > 0 else 0.0
        g_val = math.sqrt(scaled_color.y()) if scaled_color.y() > 0 else 0.0
        b_val = math.sqrt(scaled_color.z()) if scaled_color.z() > 0 else 0.0
        # Translate to byte range [0, 255]
        ir = int(256 * max(0.0, min(0.999, r_val)))
        ig = int(256 * max(0.0, min(0.999, g_val)))
        ib = int(256 * max(0.0, min(0.999, b_val)))
        row_rgb.append(f"{ir} {ig} {ib}")
    return j, "  ".join(row_rgb)


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

        self.debug = False
        self.is_scaled = False
        self.scale_fac = 1.0
        self.is_resize = False
        self.scaled_width = 0
        self.scaled_height = 0



    # fastmath=True is equivalent to -O3 -ffast-math
    #parallel=True uses OpenMP across all your CPU cores!
    def render(self, world):
        self.initialize()
        
        num_cores = os.cpu_count() or 4
        if self.debug:
            sys.stderr.write(f"\n[+] Rendering in parallel using {num_cores} CPU cores...\n")
        # Prepare tasks for all scanlines
        tasks = [
            (j, self.image_width, self.samples_per_pixel, self.max_depth, 
             self.pixel_samples_scale, self, world)
            for j in range(self.image_height)
        ]
        results = {}
        # Run across all CPU cores in parallel:
        with ProcessPoolExecutor(max_workers=num_cores) as executor:
            for j, row_str in executor.map(render_single_scanline, tasks):
                results[j] = row_str
                if self.debug:
                    remaining = self.image_height - len(results)
                    sys.stderr.write(f"\rScanlines remaining: {remaining} ")
                    sys.stderr.flush()
        # Assemble scanlines in correct top-to-bottom order
        ppm_lines = [f"P3\n{self.image_width} {self.image_height}\n255"]
        for j in range(self.image_height):
            ppm_lines.append(results[j])
        ppm_image = "\n".join(ppm_lines) + "\n"
        
        if self.outfile is not None:
            self.write_file(ppm_image)
            
        if self.debug:
            sys.stderr.write("\rDone! Render complete.                     \n")
            sys.stderr.flush()
  
    def write_file(self, img):
        ppm_bytes = img.encode('utf-8') if isinstance(img, str) else img
        # 2. Wrap the buffer in an in-memory stream
        ppm_stream = io.BytesIO(ppm_bytes)
        outfile = self.outfile if self.outfile else "default.ppm"
        try:
            # 3. Open it from memory and save it natively
            with Image.open(ppm_stream) as im:
                if self.is_scaled:
                    width = int(im.width * self.scale_fac)
                    height = int(im.height * self.scale_fac)
                    out = im.resize((width, height))
                elif self.is_resize:
                    out = im.resize((self.scaled_width, self.scaled_height))
                else:
                    out = im
                out.save(outfile)
                # Automatically converts and saves to disk
        except Exception as e:
            logger.error(f"Error saving output file: {e}")
            raise ValueError(f"Error saving output file: {e}")
            
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
