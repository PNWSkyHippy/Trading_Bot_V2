# Python port of onb.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from vec3 import Vec3, cross, unit_vector


class Onb:
    def __init__(self, n):
        self.axis = [None, None, None]
        self.axis[2] = unit_vector(n)
        a = Vec3(0, 1, 0) if abs(self.axis[2].x()) > 0.9 else Vec3(1, 0, 0)
        self.axis[1] = unit_vector(cross(self.axis[2], a))
        self.axis[0] = cross(self.axis[2], self.axis[1])

    def u(self):
        return self.axis[0]

    def v(self):
        return self.axis[1]

    def w(self):
        return self.axis[2]

    def transform(self, v):
        # Transform from basis coordinates to local space.
        return (v[0] * self.axis[0]) + (v[1] * self.axis[1]) + (v[2] * self.axis[2])
