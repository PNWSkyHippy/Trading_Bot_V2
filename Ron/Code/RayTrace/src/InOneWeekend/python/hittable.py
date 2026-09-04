# Python port of hittable.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from abc import ABC, abstractmethod

from vec3 import Point3, Vec3, dot


class HitRecord:
    def __init__(self):
        self.p = Point3()
        self.normal = Vec3()
        self.mat = None
        self.t = 0.0
        self.front_face = False

    def set_face_normal(self, r, outward_normal):
        # Sets the hit record normal vector.
        # NOTE: the parameter `outward_normal` is assumed to have unit length.
        self.front_face = dot(r.direction(), outward_normal) < 0
        self.normal = outward_normal if self.front_face else -outward_normal

    def copy_from(self, other):
        self.p = other.p
        self.normal = other.normal
        self.mat = other.mat
        self.t = other.t
        self.front_face = other.front_face


class Hittable(ABC):
    @abstractmethod
    def hit(self, r, ray_t, rec):
        raise NotImplementedError
