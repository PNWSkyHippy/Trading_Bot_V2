from math import sqrt
from hittables import HitRecord, Hittable
import ray as ry
from vectors import dot  # <-- Import your standalone dot function here


class Sphere(Hittable):
    def __init__(self, center, radius: float):
        self.center = center
        self.radius = max(0.0, float(radius))

    def hit(self, r: Ray, ray_tmin: float, ray_tmax: float, rec: HitRecord) -> bool:

        oc = self.center - r.origin()
        a = r.direction().length_squared()
        h = dot(r.direction(), oc)
        c = oc.length_squared() - self.radius * self.radius

        discriminant = h * h - a * c
        if discriminant < 0:
            return False

        sqrtd = sqrt(discriminant)

        # Find the nearest root that lies in the acceptable range [ray_tmin, ray_tmax]
        root = (h - sqrtd) / a
        if root <= ray_tmin or ray_tmax <= root:
            root = (h + sqrtd) / a
            if root <= ray_tmin or ray_tmax <= root:
                return False

        # Record collision info
        rec.t = root
        rec.p = r.at(rec.t)
        rec.normal = (rec.p - self.center) / self.radius

        return True


def hit_sphere(center, radius, r):
    oc = center - r.origin()
    a = r.direction().length_squared()
    h = dot(r.direction(), oc)
    c = oc.length_squared() - radius * radius
    discriminant = (h * h) - (a * c)

    if discriminant < 0:
        return -1.0
    else:
        return (h - sqrt(discriminant)) / a
