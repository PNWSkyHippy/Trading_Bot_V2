# Python port of material.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math

from color import Color
from ray import Ray
from rtweekend import random_double
from vec3 import (
    dot,
    random_unit_vector,
    reflect,
    refract,
    unit_vector,
)


class Material:
    def scatter(self, r_in, rec):
        return None


class Lambertian(Material):
    def __init__(self, albedo):
        self.albedo = albedo

    def scatter(self, r_in, rec):
        scatter_direction = rec.normal + random_unit_vector()

        # Catch degenerate scatter direction
        if scatter_direction.near_zero():
            scatter_direction = rec.normal

        scattered = Ray(rec.p, scatter_direction)
        attenuation = self.albedo
        return attenuation, scattered


class Metal(Material):
    def __init__(self, albedo, fuzz):
        self.albedo = albedo
        self.fuzz = fuzz if fuzz < 1 else 1

    def scatter(self, r_in, rec):
        reflected = reflect(r_in.direction(), rec.normal)
        reflected = unit_vector(reflected) + (self.fuzz * random_unit_vector())
        scattered = Ray(rec.p, reflected)
        attenuation = self.albedo
        if dot(scattered.direction(), rec.normal) > 0:
            return attenuation, scattered
        return None


class Dielectric(Material):
    def __init__(self, refraction_index):
        # Refractive index in vacuum or air, or the ratio of the material's refractive index over
        # the refractive index of the enclosing media
        self.refraction_index = refraction_index

    def scatter(self, r_in, rec):
        attenuation = Color(1.0, 1.0, 1.0)
        ri = (1.0 / self.refraction_index) if rec.front_face else self.refraction_index

        unit_direction = unit_vector(r_in.direction())
        cos_theta = min(dot(-unit_direction, rec.normal), 1.0)
        sin_theta = math.sqrt(1.0 - cos_theta * cos_theta)

        cannot_refract = ri * sin_theta > 1.0

        if cannot_refract or self.reflectance(cos_theta, ri) > random_double():
            direction = reflect(unit_direction, rec.normal)
        else:
            direction = refract(unit_direction, rec.normal, ri)

        scattered = Ray(rec.p, direction)
        return attenuation, scattered

    @staticmethod
    def reflectance(cosine, refraction_index):
        # Use Schlick's approximation for reflectance.
        r0 = (1 - refraction_index) / (1 + refraction_index)
        r0 = r0 * r0
        return r0 + (1 - r0) * pow((1 - cosine), 5)
