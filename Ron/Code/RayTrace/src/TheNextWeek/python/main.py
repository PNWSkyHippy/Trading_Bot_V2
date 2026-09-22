# Python port of main.cc
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
import argparse, sys, logging
from bvh import BvhNode
from camera import Camera
from color import Color
from constant_medium import ConstantMedium
from hittable import RotateY, Translate
from hittable_list import HittableList
from material import Dielectric, DiffuseLight, Lambertian, Metal
from quad import Quad, box
from rtweekend import random_double
from sphere import Sphere
from texture import CheckerTexture, ImageTexture, NoiseTexture
from vec3 import Point3, Vec3
from local_functions import setup_logging


def bouncing_spheres():
    world = HittableList()

    checker = CheckerTexture(0.32, Color(0.2, 0.3, 0.1), Color(0.9, 0.9, 0.9))
    world.add(Sphere(Point3(0, -1000, 0), 1000, Lambertian(checker)))

    for a in range(-11, 11):
        for b in range(-11, 11):
            choose_mat = random_double()
            center = Point3(a + 0.9 * random_double(), 0.2, b + 0.9 * random_double())

            if (center - Point3(4, 0.2, 0)).length() > 0.9:
                if choose_mat < 0.8:
                    albedo = Color.random() * Color.random()
                    sphere_material = Lambertian(albedo)
                    center2 = center + Vec3(0, random_double(0, 0.5), 0)
                    world.add(Sphere(center, center2, 0.2, sphere_material))
                elif choose_mat < 0.95:
                    albedo = Color.random(0.5, 1)
                    fuzz = random_double(0, 0.5)
                    sphere_material = Metal(albedo, fuzz)
                    world.add(Sphere(center, 0.2, sphere_material))
                else:
                    sphere_material = Dielectric(1.5)
                    world.add(Sphere(center, 0.2, sphere_material))

    world.add(Sphere(Point3(0, 1, 0), 1.0, Dielectric(1.5)))
    world.add(Sphere(Point3(-4, 1, 0), 1.0, Lambertian(Color(0.4, 0.2, 0.1))))
    world.add(Sphere(Point3(4, 1, 0), 1.0, Metal(Color(0.7, 0.6, 0.5), 0.0)))

    world = HittableList(BvhNode(world))

    cam = Camera()
    cam.aspect_ratio = 16.0 / 9.0
    cam.image_width = 400
    cam.samples_per_pixel = 100
    cam.max_depth = 50
    cam.background = Color(0.70, 0.80, 1.00)
    cam.vfov = 20
    cam.lookfrom = Point3(13, 2, 3)
    cam.lookat = Point3(0, 0, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0.6
    cam.focus_dist = 10.0
    cam.render(world)


def checkered_spheres():
    world = HittableList()
    checker = CheckerTexture(0.32, Color(0.2, 0.3, 0.1), Color(0.9, 0.9, 0.9))
    world.add(Sphere(Point3(0, -10, 0), 10, Lambertian(checker)))
    world.add(Sphere(Point3(0, 10, 0), 10, Lambertian(checker)))

    cam = Camera()
    cam.aspect_ratio = 16.0 / 9.0
    cam.image_width = 400
    cam.samples_per_pixel = 100
    cam.max_depth = 50
    cam.background = Color(0.70, 0.80, 1.00)
    cam.vfov = 20
    cam.lookfrom = Point3(13, 2, 3)
    cam.lookat = Point3(0, 0, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(world)


def earth():
    earth_texture = ImageTexture("earthmap.jpg")
    earth_surface = Lambertian(earth_texture)
    globe = Sphere(Point3(0, 0, 0), 2, earth_surface)

    cam = Camera()
    cam.aspect_ratio = 16.0 / 9.0
    cam.image_width = 400
    cam.samples_per_pixel = 100
    cam.max_depth = 50
    cam.background = Color(0.70, 0.80, 1.00)
    cam.vfov = 20
    cam.lookfrom = Point3(0, 0, 12)
    cam.lookat = Point3(0, 0, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(HittableList(globe))


def perlin_spheres():
    world = HittableList()
    pertext = NoiseTexture(4)
    world.add(Sphere(Point3(0, -1000, 0), 1000, Lambertian(pertext)))
    world.add(Sphere(Point3(0, 2, 0), 2, Lambertian(pertext)))

    cam = Camera()
    cam.aspect_ratio = 16.0 / 9.0
    cam.image_width = 400
    cam.samples_per_pixel = 100
    cam.max_depth = 50
    cam.background = Color(0.70, 0.80, 1.00)
    cam.vfov = 20
    cam.lookfrom = Point3(13, 2, 3)
    cam.lookat = Point3(0, 0, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(world)


def quads():
    world = HittableList()

    left_red = Lambertian(Color(1.0, 0.2, 0.2))
    back_green = Lambertian(Color(0.2, 1.0, 0.2))
    right_blue = Lambertian(Color(0.2, 0.2, 1.0))
    upper_orange = Lambertian(Color(1.0, 0.5, 0.0))
    lower_teal = Lambertian(Color(0.2, 0.8, 0.8))

    world.add(Quad(Point3(-3, -2, 5), Vec3(0, 0, -4), Vec3(0, 4, 0), left_red))
    world.add(Quad(Point3(-2, -2, 0), Vec3(4, 0, 0), Vec3(0, 4, 0), back_green))
    world.add(Quad(Point3(3, -2, 1), Vec3(0, 0, 4), Vec3(0, 4, 0), right_blue))
    world.add(Quad(Point3(-2, 3, 1), Vec3(4, 0, 0), Vec3(0, 0, 4), upper_orange))
    world.add(Quad(Point3(-2, -3, 5), Vec3(4, 0, 0), Vec3(0, 0, -4), lower_teal))

    cam = Camera()
    cam.aspect_ratio = 1.0
    cam.image_width = 400
    cam.samples_per_pixel = 100
    cam.max_depth = 50
    cam.background = Color(0.70, 0.80, 1.00)
    cam.vfov = 80
    cam.lookfrom = Point3(0, 0, 9)
    cam.lookat = Point3(0, 0, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(world)


def simple_light():
    world = HittableList()
    pertext = NoiseTexture(4)
    world.add(Sphere(Point3(0, -1000, 0), 1000, Lambertian(pertext)))
    world.add(Sphere(Point3(0, 2, 0), 2, Lambertian(pertext)))

    difflight = DiffuseLight(Color(4, 4, 4))
    world.add(Sphere(Point3(0, 7, 0), 2, difflight))
    world.add(Quad(Point3(3, 1, -2), Vec3(2, 0, 0), Vec3(0, 2, 0), difflight))

    cam = Camera()
    cam.aspect_ratio = 16.0 / 9.0
    cam.image_width = 400
    cam.samples_per_pixel = 100
    cam.max_depth = 50
    cam.background = Color(0, 0, 0)
    cam.vfov = 20
    cam.lookfrom = Point3(26, 3, 6)
    cam.lookat = Point3(0, 2, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(world)


def cornell_box():
    world = HittableList()

    red = Lambertian(Color(0.65, 0.05, 0.05))
    white = Lambertian(Color(0.73, 0.73, 0.73))
    green = Lambertian(Color(0.12, 0.45, 0.15))
    light = DiffuseLight(Color(15, 15, 15))

    world.add(Quad(Point3(555, 0, 0), Vec3(0, 555, 0), Vec3(0, 0, 555), green))
    world.add(Quad(Point3(0, 0, 0), Vec3(0, 555, 0), Vec3(0, 0, 555), red))
    world.add(Quad(Point3(343, 554, 332), Vec3(-130, 0, 0), Vec3(0, 0, -105), light))
    world.add(Quad(Point3(0, 0, 0), Vec3(555, 0, 0), Vec3(0, 0, 555), white))
    world.add(Quad(Point3(555, 555, 555), Vec3(-555, 0, 0), Vec3(0, 0, -555), white))
    world.add(Quad(Point3(0, 0, 555), Vec3(555, 0, 0), Vec3(0, 555, 0), white))

    box1 = box(Point3(0, 0, 0), Point3(165, 330, 165), white)
    box1 = RotateY(box1, 15)
    box1 = Translate(box1, Vec3(265, 0, 295))
    world.add(box1)

    box2 = box(Point3(0, 0, 0), Point3(165, 165, 165), white)
    box2 = RotateY(box2, -18)
    box2 = Translate(box2, Vec3(130, 0, 65))
    world.add(box2)

    cam = Camera()
    cam.aspect_ratio = 1.0
    cam.image_width = 600
    cam.samples_per_pixel = 200
    cam.max_depth = 50
    cam.background = Color(0, 0, 0)
    cam.vfov = 40
    cam.lookfrom = Point3(278, 278, -800)
    cam.lookat = Point3(278, 278, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(world)


def cornell_smoke():
    world = HittableList()

    red = Lambertian(Color(0.65, 0.05, 0.05))
    white = Lambertian(Color(0.73, 0.73, 0.73))
    green = Lambertian(Color(0.12, 0.45, 0.15))
    light = DiffuseLight(Color(7, 7, 7))

    world.add(Quad(Point3(555, 0, 0), Vec3(0, 555, 0), Vec3(0, 0, 555), green))
    world.add(Quad(Point3(0, 0, 0), Vec3(0, 555, 0), Vec3(0, 0, 555), red))
    world.add(Quad(Point3(113, 554, 127), Vec3(330, 0, 0), Vec3(0, 0, 305), light))
    world.add(Quad(Point3(0, 555, 0), Vec3(555, 0, 0), Vec3(0, 0, 555), white))
    world.add(Quad(Point3(0, 0, 0), Vec3(555, 0, 0), Vec3(0, 0, 555), white))
    world.add(Quad(Point3(0, 0, 555), Vec3(555, 0, 0), Vec3(0, 555, 0), white))

    box1 = box(Point3(0, 0, 0), Point3(165, 330, 165), white)
    box1 = RotateY(box1, 15)
    box1 = Translate(box1, Vec3(265, 0, 295))

    box2 = box(Point3(0, 0, 0), Point3(165, 165, 165), white)
    box2 = RotateY(box2, -18)
    box2 = Translate(box2, Vec3(130, 0, 65))

    world.add(ConstantMedium(box1, 0.01, Color(0, 0, 0)))
    world.add(ConstantMedium(box2, 0.01, Color(1, 1, 1)))

    cam = Camera()
    cam.aspect_ratio = 1.0
    cam.image_width = 600
    cam.samples_per_pixel = 200
    cam.max_depth = 50
    cam.background = Color(0, 0, 0)
    cam.vfov = 40
    cam.lookfrom = Point3(278, 278, -800)
    cam.lookat = Point3(278, 278, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(world)


def final_scene(image_width, samples_per_pixel, max_depth):
    boxes1 = HittableList()
    ground = Lambertian(Color(0.48, 0.83, 0.53))

    boxes_per_side = 20
    for i in range(boxes_per_side):
        for j in range(boxes_per_side):
            w = 100.0
            x0 = -1000.0 + i * w
            z0 = -1000.0 + j * w
            y0 = 0.0
            x1 = x0 + w
            y1 = random_double(1, 101)
            z1 = z0 + w
            boxes1.add(box(Point3(x0, y0, z0), Point3(x1, y1, z1), ground))

    world = HittableList()
    world.add(BvhNode(boxes1))

    light = DiffuseLight(Color(7, 7, 7))
    world.add(Quad(Point3(123, 554, 147), Vec3(300, 0, 0), Vec3(0, 0, 265), light))

    center1 = Point3(400, 400, 200)
    center2 = center1 + Vec3(30, 0, 0)
    sphere_material = Lambertian(Color(0.7, 0.3, 0.1))
    world.add(Sphere(center1, center2, 50, sphere_material))

    world.add(Sphere(Point3(260, 150, 45), 50, Dielectric(1.5)))
    world.add(Sphere(Point3(0, 150, 145), 50, Metal(Color(0.8, 0.8, 0.9), 1.0)))

    boundary = Sphere(Point3(360, 150, 145), 70, Dielectric(1.5))
    world.add(boundary)
    world.add(ConstantMedium(boundary, 0.2, Color(0.2, 0.4, 0.9)))
    boundary = Sphere(Point3(0, 0, 0), 5000, Dielectric(1.5))
    world.add(ConstantMedium(boundary, 0.0001, Color(1, 1, 1)))

    emat = Lambertian(ImageTexture("earthmap.jpg"))
    world.add(Sphere(Point3(400, 200, 400), 100, emat))
    pertext = NoiseTexture(0.2)
    world.add(Sphere(Point3(220, 280, 300), 80, Lambertian(pertext)))

    boxes2 = HittableList()
    white = Lambertian(Color(0.73, 0.73, 0.73))
    for _j in range(1000):
        boxes2.add(Sphere(Point3.random(0, 165), 10, white))

    world.add(Translate(RotateY(BvhNode(boxes2), 15), Vec3(-100, 270, 395)))

    cam = Camera()
    cam.aspect_ratio = 1.0
    cam.image_width = image_width
    cam.samples_per_pixel = samples_per_pixel
    cam.max_depth = max_depth
    cam.background = Color(0, 0, 0)
    cam.vfov = 40
    cam.lookfrom = Point3(478, 278, -600)
    cam.lookat = Point3(278, 278, 0)
    cam.vup = Vec3(0, 1, 0)
    cam.defocus_angle = 0
    cam.render(world)


file_formats = ["bmp", "gif", "ico", "jpg", "pcx", "png", "ppm", "tga", "tif"]


def main(logger):

    def wide_formatter(prog):
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )

    parser = argparse.ArgumentParser(
        description="convert ppm tp jpg",
        epilog="""\
Usage examples:
    make_ppm.py -i <input file> -o <output file>
""",
        formatter_class=wide_formatter,
    )

    parser.add_argument(
        "-o",
        "--outfile",
        metavar="",
        help="\tpath and name of output file",
    )
    parser.add_argument(
        "-f",
        "--format",
        metavar="",
        help="\tfile format to output to",
    )

    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="\tlist supported file formats",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="\tif give, prints extra debug info during render",
    )

    parser.add_argument(
        "-p",
        "--printout",
        action="store_true",
        help="\tif setm, copy of the output in R G B triplets sent to screen (> yoourfile.ppm)",
    )

    parser.add_argument(
        "-r",
        "--resize",
        metavar="",
        help="\tWidth, Height to resize image to",
    )

    parser.add_argument(
        "-w",
        "--width",
        metavar="",
        help="\tWidth to create the initial 16/9 aspect image to. Defaults to 1200",
    )

    parser.add_argument(
        "-s",
        "--scale",
        metavar="",
        help="\tFactor to cle image by <0.1 to 10>",
    )

    parser.add_argument(
        "-c",
        "--scene",
        metavar="",
        help="\tscene <1-9>       Scene to render (1: Bouncing Spheres, 2: Checkered Spheres,\n"
        "                            3: Earth, 4: Perlin Spheres, 5: Quads, 6: Simple Light,\n"
        "                            7: Cornell Box, 8: Cornell Smoke, 9: Final Scene (default: 9))\n",
    )

    args = parser.parse_args()

    scene = int(args.scene) if args.scene else 9

    if args.list:
        i = 1
        out_string = ""
        for file in file_formats:
            out_string += f"{file}\t"
            if i % 3 == 0:
                out_string += "\n"
            i += 1
        logger.info(f"Supported Formats:\n{out_string}")
        sys.exit(2)
    format = args.format if args.format else None
    outfile = args.outfile if args.outfile else None
    printout = args.printout if args.printout else False
    render_width = int(args.width) if args.width else 1200
    debug = args.debug if args.debug else False

    width, height = (
        [int(x.strip()) for x in args.resize.split(",")] if args.resize else (0, 0)
    )
    is_resize = True if args.resize else False

    is_scaled = True if args.scale else False
    scale_fac = float(args.scale) if args.scale else 1.0
    scale_fac = max(0.1, min(10.0, scale_fac))

    is_resize = False if is_scaled else is_resize

    if outfile:
        if not format:
            if "." in outfile:
                ext = outfile.rsplit(".", 1)[1].lower()
                if ext in file_formats:
                    format = ext
                else:
                    logger.error(
                        f"Error: When giving an output filename you must include -f <File Format to create>"
                    )
                    sys.exit(5)
            else:
                logger.error(
                    "Error: When giving an output filename you must include -f <File Format to create>"
                )
                sys.exit(5)

            if format not in file_formats:
                raise ValueError(f"Error: {format} format not supported")

            if "." in outfile:
                f, _ = outfile.rsplit(".", 1)
                outfile = f + "." + format
            else:
                outfile = outfile + "." + format

    if scene == 1:
        bouncing_spheres()
    elif scene == 2:
        checkered_spheres()
    elif scene == 3:
        earth()
    elif scene == 4:
        perlin_spheres()
    elif scene == 5:
        quads()
    elif scene == 6:
        simple_light()
    elif scene == 7:
        cornell_box()
    elif scene == 8:
        cornell_smoke()
    elif scene == 9:
        final_scene(800, 10000, 40)
    else:
        final_scene(400, 250, 4)


if __name__ == "__main__":
    setup_logging("file.log")
    log = logging.getLogger(__name__)
    #    log.debug("file only")
    #    log.info("stdout + file")
    #    log.warning("stdout + file")
    #    log.error("stderr + file")
    main(log)
