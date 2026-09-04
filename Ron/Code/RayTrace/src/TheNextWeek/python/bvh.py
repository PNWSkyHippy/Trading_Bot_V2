# Python port of bvh.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from aabb import Aabb
from hittable import Hittable
from hittable_list import HittableList
from interval import Interval


class BvhNode(Hittable):
    def __init__(self, objects, start=0, end=None):
        if isinstance(objects, HittableList):
            # Copy the list, matching the C++ constructor that takes hittable_list by value.
            objects = list(objects.objects)
            start = 0
            end = len(objects)
        elif end is None:
            end = len(objects)

        self.bbox = Aabb.empty
        for object_index in range(start, end):
            self.bbox = Aabb(self.bbox, objects[object_index].bounding_box())

        axis = self.bbox.longest_axis()
        object_span = end - start

        if object_span == 1:
            self.left = self.right = objects[start]
        elif object_span == 2:
            self.left = objects[start]
            self.right = objects[start + 1]
        else:
            objects[start:end] = sorted(
                objects[start:end],
                key=lambda h: h.bounding_box().axis_interval(axis).min,
            )
            mid = start + object_span // 2
            self.left = BvhNode(objects, start, mid)
            self.right = BvhNode(objects, mid, end)

    def hit(self, r, ray_t, rec):
        if not self.bbox.hit(r, ray_t):
            return False

        hit_left = self.left.hit(r, ray_t, rec)
        hit_right = self.right.hit(
            r, Interval(ray_t.min, rec.t if hit_left else ray_t.max), rec
        )
        return hit_left or hit_right

    def bounding_box(self):
        return self.bbox
