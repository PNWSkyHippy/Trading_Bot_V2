# Python port of main.cc
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from camera import Camera
from color import Color
from hittable import RotateY, Translate
from hittable_list import HittableList
from material import Dielectric, DiffuseLight, Lambertian
from quad import Quad, box
from sphere import Sphere
from vec3 import Point3, Vec3


def main():
    world = HittableList()

    red = Lambertian(Color(0.65, 0.05, 0.05))
    white = Lambertian(Color(0.73, 0.73, 0.73))
    green = Lambertian(Color(0.12, 0.45, 0.15))
    light = DiffuseLight(Color(15, 15, 15))

    # Cornell box sides
    world.add(Quad(Point3(555, 0, 0), Vec3(0, 0, 555), Vec3(0, 555, 0), green))
    world.add(Quad(Point3(0, 0, 555), Vec3(0, 0, -555), Vec3(0, 555, 0), red))
    world.add(Quad(Point3(0, 555, 0), Vec3(555, 0, 0), Vec3(0, 0, 555), white))
    world.add(Quad(Point3(0, 0, 555), Vec3(555, 0, 0), Vec3(0, 0, -555), white))
    world.add(Quad(Point3(555, 0, 555), Vec3(-555, 0, 0), Vec3(0, 555, 0), white))

    # Light
    world.add(Quad(Point3(213, 554, 227), Vec3(130, 0, 0), Vec3(0, 0, 105), light))

    # Box
    box1 = box(Point3(0, 0, 0), Point3(165, 330, 165), white)
    box1 = RotateY(box1, 15)
    box1 = Translate(box1, Vec3(265, 0, 295))
    world.add(box1)

    # Glass Sphere
    glass = Dielectric(1.5)
    world.add(Sphere(Point3(190, 90, 190), 90, glass))

    # Light Sources
    empty_material = None
    lights = HittableList()
    lights.add(Quad(Point3(343, 554, 332), Vec3(-130, 0, 0), Vec3(0, 0, -105), empty_material))
    lights.add(Sphere(Point3(190, 90, 190), 90, empty_material))

    cam = Camera()

    cam.aspect_ratio = 1.0
    cam.image_width = 600
    cam.samples_per_pixel = 100
    cam.max_depth = 50
    cam.background = Color(0, 0, 0)

    cam.vfov = 40
    cam.lookfrom = Point3(278, 278, -800)
    cam.lookat = Point3(278, 278, 0)
    cam.vup = Vec3(0, 1, 0)

    cam.defocus_angle = 0

    cam.render(world, lights)


if __name__ == "__main__":
    main()
