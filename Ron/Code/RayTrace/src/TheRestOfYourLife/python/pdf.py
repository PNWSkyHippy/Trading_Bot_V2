# Python port of pdf.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from abc import ABC, abstractmethod

from hittable_list import HittableList  # matches #include "hittable_list.h"
from onb import Onb
from rtweekend import pi, random_double
from vec3 import dot, random_cosine_direction, random_unit_vector, unit_vector


class Pdf(ABC):
    @abstractmethod
    def value(self, direction):
        raise NotImplementedError

    @abstractmethod
    def generate(self):
        raise NotImplementedError


class SpherePdf(Pdf):
    def value(self, direction):
        return 1 / (4 * pi)

    def generate(self):
        return random_unit_vector()


class CosinePdf(Pdf):
    def __init__(self, w):
        self.uvw = Onb(w)

    def value(self, direction):
        cosine_theta = dot(unit_vector(direction), self.uvw.w())
        return max(0, cosine_theta / pi)

    def generate(self):
        return self.uvw.transform(random_cosine_direction())


class HittablePdf(Pdf):
    def __init__(self, objects, origin):
        self.objects = objects
        self.origin = origin

    def value(self, direction):
        return self.objects.pdf_value(self.origin, direction)

    def generate(self):
        return self.objects.random(self.origin)


class MixturePdf(Pdf):
    def __init__(self, p0, p1):
        self.p = [p0, p1]

    def value(self, direction):
        return 0.5 * self.p[0].value(direction) + 0.5 * self.p[1].value(direction)

    def generate(self):
        if random_double() < 0.5:
            return self.p[0].generate()
        return self.p[1].generate()
