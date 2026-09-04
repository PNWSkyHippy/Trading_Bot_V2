# Python port of color.h
# Originally written in 2020 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math

from interval import Interval
from vec3 import Vec3

Color = Vec3


def linear_to_gamma(linear_component):
    if linear_component > 0:
        return math.sqrt(linear_component)
    return 0


_INTENSITY = Interval(0.000, 0.999)


def write_color(out, pixel_color):
    r = pixel_color.x()
    g = pixel_color.y()
    b = pixel_color.z()

    # Replace NaN components with zero.
    if r != r:
        r = 0.0
    if g != g:
        g = 0.0
    if b != b:
        b = 0.0

    # Apply a linear to gamma transform for gamma 2
    r = linear_to_gamma(r)
    g = linear_to_gamma(g)
    b = linear_to_gamma(b)

    # Translate the [0,1] component values to the byte range [0,255].
    rbyte = int(256 * _INTENSITY.clamp(r))
    gbyte = int(256 * _INTENSITY.clamp(g))
    bbyte = int(256 * _INTENSITY.clamp(b))

    # Write out the pixel color components.
    out.write(f"{rbyte} {gbyte} {bbyte}\n")
