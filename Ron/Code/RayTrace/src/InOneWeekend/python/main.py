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
from hittable_list import HittableList
from material import Dielectric, Lambertian, Metal
from rtweekend import random_double
from sphere import Sphere
from vec3 import Point3, Vec3
import argparse, sys, logging
from local_functions import setup_logging


file_formats = [
                "bmp",  "gif",  "ico", 
                "jpg",  "pcx",  "png", 
                "ppm",  "tga",  "tif"
            ]       

def main(logger):

    def wide_formatter(prog):
        return (argparse.RawDescriptionHelpFormatter(prog,width=110,max_help_position=46,))
    
    parser = argparse.ArgumentParser(
            description="convert ppm tp jpg",
            epilog="""\
Usage examples:
    make_ppm.py -i <input file> -o <output file>
""",
            formatter_class=wide_formatter,
    )
    
    parser.add_argument("-o", "--outfile", metavar="",
        help="\tpath and name of output file",
    )        
    parser.add_argument("-f", "--format", metavar="",
        help="\tfile format to output to",
    )
    
    parser.add_argument("-l", "--list", action="store_true",
        help="\tlist supported file formats",
    )
    
    parser.add_argument("-d", "--debug", action="store_true",
        help="\tif give, prints extra debug info during render",
    )

    parser.add_argument("-p", "--printout", action="store_true",
        help="\tif setm, copy of the output in R G B triplets sent to screen (> yoourfile.ppm)",
    )
    
    parser.add_argument("-r", "--resize", metavar="",
        help="\tWidth, Height to resize image to",
    )
        
    parser.add_argument("-w", "--width", metavar="",
        help="\tWidth to create the initial 16/9 aspect image to. Defaults to 1200",
    )
   
    parser.add_argument("-s", "--scale", metavar="",
        help="\tFactor to cle image by <0.1 to 10>",
    )
    args = parser.parse_args()
  
    if args.list:
         i = 1
         out_string = ""
         for file in file_formats:
             out_string += f'{file}\t'
             if i % 3 == 0:
                 out_string += '\n'
             i += 1
         logger.info(f'Supported Formats:\n{out_string}')
         sys.exit(2)
    format = args.format if args.format else None
    outfile = args.outfile if args.outfile else None
    printout = args.printout if args.printout else False
    render_width = int(args.width) if args.width else 1200
    debug = args.debug if args.debug else False

    width, height = [int(x.strip()) for x in args.resize.split(",")] if args.resize else (0, 0)
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
                    logger.error(f"Error: When giving an output filename you must include -f <File Format to create>")
                    sys.exit(5)
            else:
                logger.error("Error: When giving an output filename you must include -f <File Format to create>")
                sys.exit(5)

        if format not in file_formats:
            raise ValueError(f"Error: {format} format not supported")

        if "." in outfile:
            f, _ = outfile.rsplit(".", 1)
            outfile = f + "." + format
        else:
            outfile = outfile + "." + format
        
    world = HittableList()

    ground_material = Lambertian(Color(0.5, 0.5, 0.5))
    world.add(Sphere(Point3(0, -1000, 0), 1000, ground_material))

    for a in range(-11, 11):
        for b in range(-11, 11):
            choose_mat = random_double()
            center = Point3(a + 0.9 * random_double(), 0.2, b + 0.9 * random_double())

            if (center - Point3(4, 0.2, 0)).length() > 0.9:
                if choose_mat < 0.8:
                    # diffuse
                    albedo = Color.random() * Color.random()
                    sphere_material = Lambertian(albedo)
                    world.add(Sphere(center, 0.2, sphere_material))
                elif choose_mat < 0.95:
                    # metal
                    albedo = Color.random(0.5, 1)
                    fuzz = random_double(0, 0.5)
                    sphere_material = Metal(albedo, fuzz)
                    world.add(Sphere(center, 0.2, sphere_material))
                else:
                    # glass
                    sphere_material = Dielectric(1.5)
                    world.add(Sphere(center, 0.2, sphere_material))

    material1 = Dielectric(1.5)
    world.add(Sphere(Point3(0, 1, 0), 1.0, material1))

    material2 = Lambertian(Color(0.4, 0.2, 0.1))
    world.add(Sphere(Point3(-4, 1, 0), 1.0, material2))

    material3 = Metal(Color(0.7, 0.6, 0.5), 0.0)
    world.add(Sphere(Point3(4, 1, 0), 1.0, material3))

    cam = Camera()
    cam.is_scaled = is_scaled
    cam.debug = debug
    cam.is_resize = is_resize
    cam.scale_fac = scale_fac
    cam.scaled_height = height
    cam.scaled_width = width
    cam.outfile = outfile
    cam.printout = printout

    if is_resize and width > 0 and height > 0:
        render_width = width
        cam.aspect_ratio = float(width) / float(height)
    else:
        cam.aspect_ratio = 16.0 / 9.0
        if is_scaled:
            render_width = int(render_width * scale_fac)

    cam.image_width = render_width
    cam.samples_per_pixel = 10
    cam.max_depth = 20

    cam.vfov = 20
    cam.lookfrom = Point3(13, 2, 3)
    cam.lookat = Point3(0, 0, 0)
    cam.vup = Vec3(0, 1, 0)

    cam.defocus_angle = 0.6
    cam.focus_dist = 10.0

    cam.render(world)

if __name__ == "__main__":
    setup_logging("file.log")
    log = logging.getLogger(__name__)
#    log.debug("file only")
#    log.info("stdout + file")
#    log.warning("stdout + file")
#    log.error("stderr + file")
    main(log)