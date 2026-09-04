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

logger = logging.getLogger(__name__)
file_formats = [
                "bmp",  "gif",  "ico", 
                "jpg",  "pcx",  "png", 
                "ppm",  "tga",  "tif"
            ]       

def main():
    
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

    parser.add_argument("-p", "--printout", action="store_true",
        help="\tif setm, copy of the output in R G B triplets sent to screen (> yoourfile.ppm)",
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
         print(f'Supported Formats:\n{out_string}')
         sys.exit(2)
    format = args.format if args.format else False
    outfile = args.outfile if args.outfile else False    
    printout = args.printout if args.printout else False

    if outfile and not format:
         logger.info('Error: When giving an output filename you must include  -f <File Format to create>')
         sys.exit(5)
    if outfile and (format not in file_formats):   
        raise ValueError(f'Error: {e} format not supported')               
 
    out_ext = False
    try:
        f, e = outfile.split(".")
        out_ext = True
    except:
        nut_ext = False
      
    if out_ext:
        f, e = outfile.split(".")
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

    cam.outfile = outfile
    cam.printout = printout
    cam.aspect_ratio = 16.0 / 9.0
    cam.image_width = 128
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
    main()
