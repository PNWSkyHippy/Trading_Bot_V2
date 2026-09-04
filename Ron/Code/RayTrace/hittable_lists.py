from hittables import HitRecord, Hittable
from rays import Ray


class HittableList(Hittable):
    def __init__(self, object=None):
        self.objects = []

        if object is not None:
            self.add(object)

    def clear(self):
        self.objects.clear()

    def add(self, object):
        self.objects.append(object)

    def hit(
        self,
        r: Ray,
        ray_tmin: float,
        ray_tmax: float,
        rec: HitRecord,
    ) -> bool:
        hit_anything = False
        closest_so_far = ray_tmax

        for object in self.objects:
            temp_rec = HitRecord()

            if object.hit(r, ray_tmin, closest_so_far, temp_rec):
                hit_anything = True
                closest_so_far = temp_rec.t

                # C++ copies temp_rec into rec. In Python, copy the fields so
                # the caller's HitRecord instance is updated too.
                rec.p = temp_rec.p
                rec.normal = temp_rec.normal
                rec.t = temp_rec.t
                rec.front_face = temp_rec.front_face

        return hit_anything
