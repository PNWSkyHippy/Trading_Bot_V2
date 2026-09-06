//==============================================================================================
// Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
//
// To the extent possible under law, the author(s) have dedicated all copyright and related and
// neighboring rights to this software to the public domain worldwide. This software is
// distributed without any warranty.
//
// You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
// along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
//==============================================================================================

#include "rtweekend.h"

#include "camera.h"
#include "hittable.h"
#include "hittable_list.h"
#include "material.h"
#include "sphere.h"

#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>

const std::vector<std::string> file_formats = {
    "bmp",  "gif",  "ico", 
    "jpg",  "pcx",  "png", 
    "ppm",  "tga",  "tif"
};

void print_help(const char* prog) {
    std::cout << "Usage: " << prog << " [options]\n\n"
              << "Options:\n"
              << "  -o, --outfile <file>    Path and name of output file\n"
              << "  -f, --format <format>   File format to output to\n"
              << "  -l, --list              List supported file formats\n"
              << "  -d, --debug             If given, prints extra debug info during render\n"
              << "  -p, --printout          If set, copy of output in RGB triplets sent to screen\n"
              << "  -r, --resize <w,h>      Width, Height to resize image to\n"
              << "  -w, --width <w>         Width to create the initial 16/9 aspect image to (default: 1200)\n"
              << "  -s, --scale <factor>    Factor to scale image by (0.1 to 10)\n"
              << "  -h, --help              Show this help message\n";
}

int main(int argc, char* argv[]) {
    std::string outfile = "";
    std::string format = "";
    bool list_formats = false;
    bool debug = false;
    bool printout = false;
    int render_width = 1200;
    bool is_resize = false;
    int resize_w = 0, resize_h = 0;
    bool is_scaled = false;
    double scale_fac = 1.0;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-h" || arg == "--help") {
            print_help(argv[0]);
            return 0;
        } else if (arg == "-l" || arg == "--list") {
            list_formats = true;
        } else if (arg == "-d" || arg == "--debug") {
            debug = true;
        } else if (arg == "-p" || arg == "--printout") {
            printout = true;
        } else if ((arg == "-o" || arg == "--outfile") && i + 1 < argc) {
            outfile = argv[++i];
        } else if ((arg == "-f" || arg == "--format") && i + 1 < argc) {
            format = argv[++i];
        } else if ((arg == "-w" || arg == "--width") && i + 1 < argc) {
            render_width = std::atoi(argv[++i]);
        } else if ((arg == "-s" || arg == "--scale") && i + 1 < argc) {
            is_scaled = true;
            scale_fac = std::atof(argv[++i]);
            if (scale_fac < 0.1) scale_fac = 0.1;
            if (scale_fac > 10.0) scale_fac = 10.0;
        } else if ((arg == "-r" || arg == "--resize") && i + 1 < argc) {
            is_resize = true;
            std::string res_str = argv[++i];
            auto comma_pos = res_str.find(',');
            if (comma_pos != std::string::npos) {
                resize_w = std::atoi(res_str.substr(0, comma_pos).c_str());
                resize_h = std::atoi(res_str.substr(comma_pos + 1).c_str());
            }
        }
    }

    if (list_formats) {
        std::cout << "Supported Formats:\n";
        int idx = 1;
        for (const auto& fmt : file_formats) {
            std::cout << fmt << "\t";
            if (idx % 3 == 0) std::cout << "\n";
            idx++;
        }
        return 0;
    }

    if (is_scaled) {
        is_resize = false;
    }

    if (!outfile.empty()) {
        if (format.empty()) {
            auto dot_pos = outfile.find_last_of('.');
            if (dot_pos != std::string::npos) {
                std::string ext = outfile.substr(dot_pos + 1);
                bool found = false;
                for (const auto& f : file_formats) {
                    if (f == ext) {
                        format = ext;
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    std::cerr << "Error: When giving an output filename you must include -f <File Format to create>\n";
                    return 5;
                }
            } else {
                std::cerr << "Error: When giving an output filename you must include -f <File Format to create>\n";
                return 5;
            }
        }

        bool format_valid = false;
        for (const auto& f : file_formats) {
            if (f == format) {
                format_valid = true;
                break;
            }
        }
        if (!format_valid) {
            std::cerr << "Error: " << format << " format not supported\n";
            return 1;
        }

        auto dot_pos = outfile.find_last_of('.');
        if (dot_pos != std::string::npos) {
            outfile = outfile.substr(0, dot_pos) + "." + format;
        } else {
            outfile = outfile + "." + format;
        }
    }

    hittable_list world;

    auto ground_material = make_shared<lambertian>(color(0.5, 0.5, 0.5));
    world.add(make_shared<sphere>(point3(0,-1000,0), 1000, ground_material));

    for (int a = -11; a < 11; a++) {
        for (int b = -11; b < 11; b++) {
            auto choose_mat = random_double();
            point3 center(a + 0.9*random_double(), 0.2, b + 0.9*random_double());

            if ((center - point3(4, 0.2, 0)).length() > 0.9) {
                shared_ptr<material> sphere_material;

                if (choose_mat < 0.8) {
                    // diffuse
                    auto albedo = color::random() * color::random();
                    sphere_material = make_shared<lambertian>(albedo);
                    world.add(make_shared<sphere>(center, 0.2, sphere_material));
                } else if (choose_mat < 0.95) {
                    // metal
                    auto albedo = color::random(0.5, 1);
                    auto fuzz = random_double(0, 0.5);
                    sphere_material = make_shared<metal>(albedo, fuzz);
                    world.add(make_shared<sphere>(center, 0.2, sphere_material));
                } else {
                    // glass
                    sphere_material = make_shared<dielectric>(1.5);
                    world.add(make_shared<sphere>(center, 0.2, sphere_material));
                }
            }
        }
    }

    auto material1 = make_shared<dielectric>(1.5);
    world.add(make_shared<sphere>(point3(0, 1, 0), 1.0, material1));

    auto material2 = make_shared<lambertian>(color(0.4, 0.2, 0.1));
    world.add(make_shared<sphere>(point3(-4, 1, 0), 1.0, material2));

    auto material3 = make_shared<metal>(color(0.7, 0.6, 0.5), 0.0);
    world.add(make_shared<sphere>(point3(4, 1, 0), 1.0, material3));

    camera cam;
    cam.is_scaled     = is_scaled;
    cam.debug         = debug;
    cam.is_resize     = is_resize;
    cam.scale_fac     = scale_fac;
    cam.scaled_height = resize_h;
    cam.scaled_width  = resize_w;
    cam.outfile       = outfile;
    cam.printout      = printout;

    if (is_resize && resize_w > 0 && resize_h > 0) {
        render_width = resize_w;
        cam.aspect_ratio = double(resize_w) / double(resize_h);
    } else {
        cam.aspect_ratio = 16.0 / 9.0;
        if (is_scaled) {
            render_width = int(render_width * scale_fac);
        }
    }

    cam.image_width       = render_width;
    cam.samples_per_pixel = 10;
    cam.max_depth         = 20;

    cam.vfov     = 20;
    cam.lookfrom = point3(13,2,3);
    cam.lookat   = point3(0,0,0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0.6;
    cam.focus_dist    = 10.0;

    cam.render(world);
    return 0;
}
