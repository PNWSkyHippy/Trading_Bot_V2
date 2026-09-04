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
from pdf import CosinePdf, SpherePdf
from ray import Ray
from rtweekend import pi, random_double
from texture import SolidColor, Texture
from vec3 import (
    dot,
    random_unit_vector,
    reflect,
    refract,
    unit_vector,
)


class ScatterRecord:
    def __init__(self):
        self.attenuation = Color()
        self.pdf_ptr = None
        self.skip_pdf = False
        self.skip_pdf_ray = Ray()


class Material:
    def emitted(self, r_in, rec, u, v, p):
        return Color(0, 0, 0)

    def scatter(self, r_in, rec, srec):
        return False

    def scattering_pdf(self, r_in, rec, scattered):
        return 0


class Lambertian(Material):
    def __init__(self, albedo_or_tex):
        if isinstance(albedo_or_tex, Texture):
            self.tex = albedo_or_tex
        else:
            self.tex = SolidColor(albedo_or_tex)

    def scatter(self, r_in, rec, srec):
        srec.attenuation = self.tex.value(rec.u, rec.v, rec.p)
        srec.pdf_ptr = CosinePdf(rec.normal)
        srec.skip_pdf = False
        return True

    def scattering_pdf(self, r_in, rec, scattered):
        cos_theta = dot(rec.normal, unit_vector(scattered.direction()))
        return 0 if cos_theta < 0 else cos_theta / pi


class Metal(Material):
    def __init__(self, albedo, fuzz):
        self.albedo = albedo
        self.fuzz = fuzz if fuzz < 1 else 1

    def scatter(self, r_in, rec, srec):
        reflected = reflect(r_in.direction(), rec.normal)
        reflected = unit_vector(reflected) + (self.fuzz * random_unit_vector())

        srec.attenuation = self.albedo
        srec.pdf_ptr = None
        srec.skip_pdf = True
        srec.skip_pdf_ray = Ray(rec.p, reflected, r_in.time())
        return True


class Dielectric(Material):
    def __init__(self, refraction_index):
        self.refraction_index = refraction_index

    def scatter(self, r_in, rec, srec):
        srec.attenuation = Color(1.0, 1.0, 1.0)
        srec.pdf_ptr = None
        srec.skip_pdf = True
        ri = (1.0 / self.refraction_index) if rec.front_face else self.refraction_index

        unit_direction = unit_vector(r_in.direction())
        cos_theta = min(dot(-unit_direction, rec.normal), 1.0)
        sin_theta = math.sqrt(1.0 - cos_theta * cos_theta)

        cannot_refract = ri * sin_theta > 1.0

        if cannot_refract or self.reflectance(cos_theta, ri) > random_double():
            direction = reflect(unit_direction, rec.normal)
        else:
            direction = refract(unit_direction, rec.normal, ri)

        srec.skip_pdf_ray = Ray(rec.p, direction, r_in.time())
        return True

    @staticmethod
    def reflectance(cosine, refraction_index):
        r0 = (1 - refraction_index) / (1 + refraction_index)
        r0 = r0 * r0
        return r0 + (1 - r0) * pow((1 - cosine), 5)


class DiffuseLight(Material):
    def __init__(self, tex_or_color):
        if isinstance(tex_or_color, Texture):
            self.tex = tex_or_color
        else:
            self.tex = SolidColor(tex_or_color)

    def emitted(self, r_in, rec, u, v, p):
        if not rec.front_face:
            return Color(0, 0, 0)
        return self.tex.value(u, v, p)


class Isotropic(Material):
    def __init__(self, albedo_or_tex):
        if isinstance(albedo_or_tex, Texture):
            self.tex = albedo_or_tex
        else:
            self.tex = SolidColor(albedo_or_tex)

    def scatter(self, r_in, rec, srec):
        srec.attenuation = self.tex.value(rec.u, rec.v, rec.p)
        srec.pdf_ptr = SpherePdf()
        srec.skip_pdf = False
        return True

    def scattering_pdf(self, r_in, rec, scattered):
        return 1 / (4 * pi)
