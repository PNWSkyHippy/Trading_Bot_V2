# Python port of texture.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from abc import ABC, abstractmethod
import math

from color import Color
from interval import Interval
from perlin import Perlin
from rtw_stb_image import RtwImage


class Texture(ABC):
    @abstractmethod
    def value(self, u, v, p):
        raise NotImplementedError


class SolidColor(Texture):
    def __init__(self, *args):
        if len(args) == 1:
            self.albedo = args[0]
        else:
            red, green, blue = args
            self.albedo = Color(red, green, blue)

    def value(self, u, v, p):
        return self.albedo


class CheckerTexture(Texture):
    def __init__(self, scale, even, odd=None):
        self.inv_scale = 1.0 / scale
        if odd is None:
            raise TypeError(
                "CheckerTexture(scale, even, odd) or CheckerTexture(scale, c1, c2)"
            )
        if hasattr(even, "value"):
            self.even = even
            self.odd = odd
        else:
            self.even = SolidColor(even)
            self.odd = SolidColor(odd)

    def value(self, u, v, p):
        x_integer = int(math.floor(self.inv_scale * p.x()))
        y_integer = int(math.floor(self.inv_scale * p.y()))
        z_integer = int(math.floor(self.inv_scale * p.z()))

        is_even = (x_integer + y_integer + z_integer) % 2 == 0
        return self.even.value(u, v, p) if is_even else self.odd.value(u, v, p)


class ImageTexture(Texture):
    def __init__(self, filename):
        self.image = RtwImage(filename)

    def value(self, u, v, p):
        # If we have no texture data, then return solid cyan as a debugging aid.
        if self.image.height() <= 0:
            return Color(0, 1, 1)

        # Clamp input texture coordinates to [0,1] x [1,0]
        u = Interval(0, 1).clamp(u)
        v = 1.0 - Interval(0, 1).clamp(v)  # Flip V to image coordinates

        i = int(u * self.image.width())
        j = int(v * self.image.height())
        pixel = self.image.pixel_data(i, j)

        color_scale = 1.0 / 255.0
        return Color(
            color_scale * pixel[0], color_scale * pixel[1], color_scale * pixel[2]
        )


class NoiseTexture(Texture):
    def __init__(self, scale):
        self.noise = Perlin()
        self.scale = scale

    def value(self, u, v, p):
        return Color(0.5, 0.5, 0.5) * (
            1 + math.sin(self.scale * p.z() + 10 * self.noise.turb(p, 7))
        )
