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


class Camera:
    def __init__(self):
        self.aspect_ratio = 1.0
        self.image_width = 100
        self.samples_per_pixel = 10
        self.max_depth = 10
        self.background = Color()

        self.vfov = 90
        self.lookfrom = Point3(0, 0, 0)
        self.lookat = Point3(0, 0, -1)
        self.vup = Vec3(0, 1, 0)

        self.defocus_angle = 0
        self.focus_dist = 10

        self.image_height = 0
        self.pixel_samples_scale = 1.0
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

        sys.stdout.write(f"P3\n{self.image_width} {self.image_height}\n255\n")

        for j in range(self.image_height):
            remaining = self.image_height - j
            sys.stderr.write(f"\rScanlines remaining: {remaining} ")
            sys.stderr.flush()
            for i in range(self.image_width):
                pixel_color = Color(0, 0, 0)
                for _sample in range(self.samples_per_pixel):
                    r = self.get_ray(i, j)
                    pixel_color += self.ray_color(r, self.max_depth, world)
                write_color(sys.stdout, self.pixel_samples_scale * pixel_color)

        sys.stderr.write("\rDone.                 \n")

    def initialize(self):
        self.image_height = int(self.image_width / self.aspect_ratio)
        self.image_height = 1 if self.image_height < 1 else self.image_height

        self.pixel_samples_scale = 1.0 / self.samples_per_pixel
        self.center = self.lookfrom

        theta = degrees_to_radians(self.vfov)
        h = math.tan(theta / 2)
        viewport_height = 2 * h * self.focus_dist
        viewport_width = viewport_height * (self.image_width / self.image_height)

        self.w = unit_vector(self.lookfrom - self.lookat)
        self.u = unit_vector(cross(self.vup, self.w))
        self.v = cross(self.w, self.u)

        viewport_u = viewport_width * self.u
        viewport_v = viewport_height * -self.v

        self.pixel_delta_u = viewport_u / self.image_width
        self.pixel_delta_v = viewport_v / self.image_height

        viewport_upper_left = (
            self.center - (self.focus_dist * self.w) - viewport_u / 2 - viewport_v / 2
        )
        self.pixel00_loc = viewport_upper_left + 0.5 * (
            self.pixel_delta_u + self.pixel_delta_v
        )

        defocus_radius = self.focus_dist * math.tan(
            degrees_to_radians(self.defocus_angle / 2)
        )
        self.defocus_disk_u = self.u * defocus_radius
        self.defocus_disk_v = self.v * defocus_radius

    def get_ray(self, i, j):
        offset = self.sample_square()
        pixel_sample = (
            self.pixel00_loc
            + ((i + offset.x()) * self.pixel_delta_u)
            + ((j + offset.y()) * self.pixel_delta_v)
        )

        ray_origin = (
            self.center if self.defocus_angle <= 0 else self.defocus_disk_sample()
        )
        ray_direction = pixel_sample - ray_origin
        ray_time = random_double()

        return Ray(ray_origin, ray_direction, ray_time)

    def sample_square(self):
        return Vec3(random_double() - 0.5, random_double() - 0.5, 0)

    def sample_disk(self, radius):
        return radius * random_in_unit_disk()

    def defocus_disk_sample(self):
        p = random_in_unit_disk()
        return self.center + (p[0] * self.defocus_disk_u) + (p[1] * self.defocus_disk_v)

    def ray_color(self, r, depth, world):
        if depth <= 0:
            return Color(0, 0, 0)

        rec = HitRecord()

        if not world.hit(r, Interval(0.001, infinity), rec):
            return self.background

        color_from_emission = rec.mat.emitted(rec.u, rec.v, rec.p)

        scattered = rec.mat.scatter(r, rec)
        if scattered is None:
            return color_from_emission

        attenuation, scattered_ray = scattered
        color_from_scatter = attenuation * self.ray_color(
            scattered_ray, depth - 1, world
        )
        return color_from_emission + color_from_scatter
