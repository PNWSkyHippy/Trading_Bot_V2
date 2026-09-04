# Python port of hittable_list.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from aabb import Aabb
from hittable import HitRecord, Hittable
from interval import Interval


class HittableList(Hittable):
    def __init__(self, obj=None):
        self.objects = []
        self.bbox = Aabb()
        if obj is not None:
            self.add(obj)

    def clear(self):
        self.objects.clear()

    def add(self, obj):
        self.objects.append(obj)
        self.bbox = Aabb(self.bbox, obj.bounding_box())

    def hit(self, r, ray_t, rec):
        temp_rec = HitRecord()
        hit_anything = False
        closest_so_far = ray_t.max

        for obj in self.objects:
            if obj.hit(r, Interval(ray_t.min, closest_so_far), temp_rec):
                hit_anything = True
                closest_so_far = temp_rec.t
                rec.copy_from(temp_rec)

        return hit_anything

    def bounding_box(self):
        return self.bbox
