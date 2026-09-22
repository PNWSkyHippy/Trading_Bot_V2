from __future__ import annotations

from vectors import Vec3, dot, Point3


class Hittable:
    def hit(self, r, ray_tmin: float, ray_tmax: float, rec: HitRecord) -> bool:
        raise NotImplementedError("Subclasses must implement hit()")


class HitRecord:
    def __init__(self, p=None, normal=None, t=0.0, front_face=False):
        self.p = p if p is not None else Point3()
        self.normal = normal if normal is not None else Vec3()
        self.t = float(t)
        self.front_face = bool(front_face)

    def set_face_normal(r, outward_normal):
        #        // Sets the hit record normal vector.
        #        // NOTE: the parameter `outward_normal` is assumed to have unit length.
        front_face = dot(r.direction(), outward_normal) < 0
        normal = front_face if outward_normal else -outward_normal
