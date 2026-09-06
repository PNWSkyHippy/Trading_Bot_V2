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

#include "bvh.h"
#include "camera.h"
#include "constant_medium.h"
#include "hittable.h"
#include "hittable_list.h"
#include "material.h"
#include "quad.h"
#include "sphere.h"
#include "texture.h"

#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>

const std::vector<std::string> file_formats = {
    "bmp",  "gif",  "ico", 
    "jpg",  "pcx",  "png", 
    "ppm",  "tga",  "tif"
};

struct camera_options {
    std::string outfile = "";
    std::string format = "";
    bool debug = false;
    bool printout = false;
    int width = 0;
    bool is_scaled = false;
    double scale_fac = 1.0;
    bool is_resize = false;
    int resize_w = 0, resize_h = 0;
};

inline void apply_options(camera& cam, const camera_options& opt) {
    if (opt.is_resize && opt.resize_w > 0 && opt.resize_h > 0) {
        cam.image_width = opt.resize_w;
        cam.aspect_ratio = double(opt.resize_w) / double(opt.resize_h);
    } else {
        if (opt.width > 0) cam.image_width = opt.width;
        if (opt.is_scaled) {
            cam.image_width = int(cam.image_width * opt.scale_fac);
        }
    }
    cam.outfile = opt.outfile;
    cam.debug = opt.debug;
    cam.printout = opt.printout;
    cam.is_scaled = opt.is_scaled;
    cam.scale_fac = opt.scale_fac;
    cam.is_resize = opt.is_resize;
    cam.scaled_width = opt.resize_w;
    cam.scaled_height = opt.resize_h;
}

void bouncing_spheres(const camera_options& opt) {
    hittable_list world;

    auto checker = make_shared<checker_texture>(0.32, color(.2, .3, .1), color(.9, .9, .9));
    world.add(make_shared<sphere>(point3(0,-1000,0), 1000, make_shared<lambertian>(checker)));

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
                    auto center2 = center + vec3(0, random_double(0,.5), 0);
                    world.add(make_shared<sphere>(center, center2, 0.2, sphere_material));
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

    world = hittable_list(make_shared<bvh_node>(world));

    camera cam;

    cam.aspect_ratio      = 16.0 / 9.0;
    cam.image_width       = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth         = 50;
    cam.background        = color(0.70, 0.80, 1.00);

    cam.vfov     = 20;
    cam.lookfrom = point3(13,2,3);
    cam.lookat   = point3(0,0,0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0.6;
    cam.focus_dist    = 10.0;

    apply_options(cam, opt);
    cam.render(world);
}


void checkered_spheres(const camera_options& opt) {
    hittable_list world;

    auto checker = make_shared<checker_texture>(0.32, color(.2, .3, .1), color(.9, .9, .9));

    world.add(make_shared<sphere>(point3(0,-10, 0), 10, make_shared<lambertian>(checker)));
    world.add(make_shared<sphere>(point3(0, 10, 0), 10, make_shared<lambertian>(checker)));

    camera cam;

    cam.aspect_ratio      = 16.0 / 9.0;
    cam.image_width       = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth         = 50;
    cam.background        = color(0.70, 0.80, 1.00);

    cam.vfov     = 20;
    cam.lookfrom = point3(13,2,3);
    cam.lookat   = point3(0,0,0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(world);
}


void earth(const camera_options& opt) {
    auto earth_texture = make_shared<image_texture>("earthmap.jpg");
    auto earth_surface = make_shared<lambertian>(earth_texture);
    auto globe = make_shared<sphere>(point3(0,0,0), 2, earth_surface);

    camera cam;

    cam.aspect_ratio      = 16.0 / 9.0;
    cam.image_width       = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth         = 50;
    cam.background        = color(0.70, 0.80, 1.00);

    cam.vfov     = 20;
    cam.lookfrom = point3(0,0,12);
    cam.lookat   = point3(0,0,0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(hittable_list(globe));
}


void perlin_spheres(const camera_options& opt) {
    hittable_list world;
  
    auto light = make_shared<diffuse_light>(color(15, 15, 15));
    auto pertext = make_shared<noise_texture>(4);
    world.add(make_shared<sphere>(point3(0,-1000,0), 1000, make_shared<lambertian>(pertext)));
    world.add(make_shared<sphere>(point3(0,2,0), 2, make_shared<lambertian>(pertext)));
    world.add(make_shared<quad>(point3(343, 554, 332), vec3(-130,0,0), vec3(0,0,-105), light));
    world.add(make_shared<quad>(point3(343, 554, 332), vec3(130,0,0), vec3(0,0,-105), light));
    world.add(make_shared<quad>(point3(343, 554, 332), vec3(-130,1300,0), vec3(0,0,-105), light));
    camera cam;

    cam.aspect_ratio      = 16.0 / 9.0;
    cam.image_width       = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth         = 50;
    cam.background        = color(0.70, 0.80, 1.00);

    cam.vfov     = 20;
    cam.lookfrom = point3(13,2,3);
    cam.lookat   = point3(0,0,0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(world);
}


void quads(const camera_options& opt) {
    hittable_list world;

    // Materials
    auto left_red     = make_shared<lambertian>(color(1.0, 0.2, 0.2));
    auto back_green   = make_shared<lambertian>(color(0.2, 1.0, 0.2));
    auto right_blue   = make_shared<lambertian>(color(0.2, 0.2, 1.0));
    auto upper_orange = make_shared<lambertian>(color(1.0, 0.5, 0.0));
    auto lower_teal   = make_shared<lambertian>(color(0.2, 0.8, 0.8));

    // Quads
    world.add(make_shared<quad>(point3(-3,-2, 5), vec3(0, 0,-4), vec3(0, 4, 0), left_red));
    world.add(make_shared<quad>(point3(-2,-2, 0), vec3(4, 0, 0), vec3(0, 4, 0), back_green));
    world.add(make_shared<quad>(point3( 3,-2, 1), vec3(0, 0, 4), vec3(0, 4, 0), right_blue));
    world.add(make_shared<quad>(point3(-2, 3, 1), vec3(4, 0, 0), vec3(0, 0, 4), upper_orange));
    world.add(make_shared<quad>(point3(-2,-3, 5), vec3(4, 0, 0), vec3(0, 0,-4), lower_teal));

    camera cam;

    cam.aspect_ratio      = 1.0;
    cam.image_width       = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth         = 50;
    cam.background        = color(0.70, 0.80, 1.00);

    cam.vfov     = 80;
    cam.lookfrom = point3(0,0,9);
    cam.lookat   = point3(0,0,0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(world);
}


void simple_light(const camera_options& opt) {
    hittable_list world;

    auto pertext = make_shared<noise_texture>(4);
    world.add(make_shared<sphere>(point3(0,-1000,0), 1000, make_shared<lambertian>(pertext)));
    world.add(make_shared<sphere>(point3(0,2,0), 2, make_shared<lambertian>(pertext)));

    auto difflight = make_shared<diffuse_light>(color(4,4,4));
    world.add(make_shared<sphere>(point3(0,7,0), 2, difflight));
    world.add(make_shared<quad>(point3(3,1,-2), vec3(2,0,0), vec3(0,2,0), difflight));

    camera cam;

    cam.aspect_ratio      = 16.0 / 9.0;
    cam.image_width       = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth         = 50;
    cam.background        = color(0,0,0);

    cam.vfov     = 20;
    cam.lookfrom = point3(26,3,6);
    cam.lookat   = point3(0,2,0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(world);
}


void cornell_box(const camera_options& opt) {
    hittable_list world;

    auto red   = make_shared<lambertian>(color(.65, .05, .05));
    auto white = make_shared<lambertian>(color(.73, .73, .73));
    auto green = make_shared<lambertian>(color(.12, .45, .15));
    auto light = make_shared<diffuse_light>(color(15, 15, 15));

    world.add(make_shared<quad>(point3(555,0,0), vec3(0,555,0), vec3(0,0,555), green));
    world.add(make_shared<quad>(point3(0,0,0), vec3(0,555,0), vec3(0,0,555), red));
    world.add(make_shared<quad>(point3(343, 554, 332), vec3(-130,0,0), vec3(0,0,-105), light));
    world.add(make_shared<quad>(point3(0,0,0), vec3(555,0,0), vec3(0,0,555), white));
    world.add(make_shared<quad>(point3(555,555,555), vec3(-555,0,0), vec3(0,0,-555), white));
    world.add(make_shared<quad>(point3(0,0,555), vec3(555,0,0), vec3(0,555,0), white));

    shared_ptr<hittable> box1 = box(point3(0,0,0), point3(165,330,165), white);
    box1 = make_shared<rotate_y>(box1, 15);
    box1 = make_shared<translate>(box1, vec3(265,0,295));
    world.add(box1);

    shared_ptr<hittable> box2 = box(point3(0,0,0), point3(165,165,165), white);
    box2 = make_shared<rotate_y>(box2, -18);
    box2 = make_shared<translate>(box2, vec3(130,0,65));
    world.add(box2);

    camera cam;

    cam.aspect_ratio      = 1.0;
    cam.image_width       = 600;
    cam.samples_per_pixel = 200;
    cam.max_depth         = 50;
    cam.background        = color(0,0,0);

    cam.vfov     = 40;
    cam.lookfrom = point3(278, 278, -800);
    cam.lookat   = point3(278, 278, 0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(world);
}


void cornell_smoke(const camera_options& opt) {
    hittable_list world;

    auto red   = make_shared<lambertian>(color(.65, .05, .05));
    auto white = make_shared<lambertian>(color(.73, .73, .73));
    auto green = make_shared<lambertian>(color(.12, .45, .15));
    auto light = make_shared<diffuse_light>(color(7, 7, 7));

    world.add(make_shared<quad>(point3(555,0,0), vec3(0,555,0), vec3(0,0,555), green));
    world.add(make_shared<quad>(point3(0,0,0), vec3(0,555,0), vec3(0,0,555), red));
    world.add(make_shared<quad>(point3(113,554,127), vec3(330,0,0), vec3(0,0,305), light));
    world.add(make_shared<quad>(point3(0,555,0), vec3(555,0,0), vec3(0,0,555), white));
    world.add(make_shared<quad>(point3(0,0,0), vec3(555,0,0), vec3(0,0,555), white));
    world.add(make_shared<quad>(point3(0,0,555), vec3(555,0,0), vec3(0,0,555), white));

    shared_ptr<hittable> box1 = box(point3(0,0,0), point3(165,330,165), white);
    box1 = make_shared<rotate_y>(box1, 15);
    box1 = make_shared<translate>(box1, vec3(265,0,295));

    shared_ptr<hittable> box2 = box(point3(0,0,0), point3(165,165,165), white);
    box2 = make_shared<rotate_y>(box2, -18);
    box2 = make_shared<translate>(box2, vec3(130,0,65));

    world.add(make_shared<constant_medium>(box1, 0.01, color(0,0,0)));
    world.add(make_shared<constant_medium>(box2, 0.01, color(1,1,1)));

    camera cam;

    cam.aspect_ratio      = 1.0;
    cam.image_width       = 600;
    cam.samples_per_pixel = 200;
    cam.max_depth         = 50;
    cam.background        = color(0,0,0);

    cam.vfov     = 40;
    cam.lookfrom = point3(278, 278, -800);
    cam.lookat   = point3(278, 278, 0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(world);
}


void final_scene(int image_width, int samples_per_pixel, int max_depth, const camera_options& opt) {
    hittable_list boxes1;
    auto ground = make_shared<lambertian>(color(0.48, 0.83, 0.53));

    int boxes_per_side = 20;
    for (int i = 0; i < boxes_per_side; i++) {
        for (int j = 0; j < boxes_per_side; j++) {
            auto w = 100.0;
            auto x0 = -1000.0 + i*w;
            auto z0 = -1000.0 + j*w;
            auto y0 = 0.0;
            auto x1 = x0 + w;
            auto y1 = random_double(1,101);
            auto z1 = z0 + w;

            boxes1.add(box(point3(x0,y0,z0), point3(x1,y1,z1), ground));
        }
    }

    hittable_list world;

    world.add(make_shared<bvh_node>(boxes1));

    auto light = make_shared<diffuse_light>(color(7, 7, 7));
    world.add(make_shared<quad>(point3(123,554,147), vec3(300,0,0), vec3(0,0,265), light));

    auto center1 = point3(400, 400, 200);
    auto center2 = center1 + vec3(30,0,0);
    auto sphere_material = make_shared<lambertian>(color(0.7, 0.3, 0.1));
    world.add(make_shared<sphere>(center1, center2, 50, sphere_material));

    world.add(make_shared<sphere>(point3(260, 150, 45), 50, make_shared<dielectric>(1.5)));
    world.add(make_shared<sphere>(
        point3(0, 150, 145), 50, make_shared<metal>(color(0.8, 0.8, 0.9), 1.0)
    ));

    auto boundary = make_shared<sphere>(point3(360,150,145), 70, make_shared<dielectric>(1.5));
    world.add(boundary);
    world.add(make_shared<constant_medium>(boundary, 0.2, color(0.2, 0.4, 0.9)));
    boundary = make_shared<sphere>(point3(0,0,0), 5000, make_shared<dielectric>(1.5));
    world.add(make_shared<constant_medium>(boundary, .0001, color(1,1,1)));

    auto emat = make_shared<lambertian>(make_shared<image_texture>("earthmap.jpg"));
    world.add(make_shared<sphere>(point3(400,200,400), 100, emat));
    auto pertext = make_shared<noise_texture>(0.2);
    world.add(make_shared<sphere>(point3(220,280,300), 80, make_shared<lambertian>(pertext)));

    hittable_list boxes2;
    auto white = make_shared<lambertian>(color(.73, .73, .73));
    int ns = 1000;
    for (int j = 0; j < ns; j++) {
        boxes2.add(make_shared<sphere>(point3::random(0,165), 10, white));
    }

    world.add(make_shared<translate>(
        make_shared<rotate_y>(
            make_shared<bvh_node>(boxes2), 15),
            vec3(-100,270,395)
        )
    );

    camera cam;

    cam.aspect_ratio      = 1.0;
    cam.image_width       = image_width;
    cam.samples_per_pixel = samples_per_pixel;
    cam.max_depth         = max_depth;
    cam.background        = color(0,0,0);

    cam.vfov     = 40;
    cam.lookfrom = point3(478, 278, -600);
    cam.lookat   = point3(278, 278, 0);
    cam.vup      = vec3(0,1,0);

    cam.defocus_angle = 0;

    apply_options(cam, opt);
    cam.render(world);
}

void print_help(const char* prog) {
    std::cout << "Usage: " << prog << " [options]\n\n"
              << "Options:\n"
              << "  -c, --scene <1-9>       Scene to render (1: Bouncing Spheres, 2: Checkered Spheres,\n"
              << "                            3: Earth, 4: Perlin Spheres, 5: Quads, 6: Simple Light,\n"
              << "                            7: Cornell Box, 8: Cornell Smoke, 9: Final Scene (default: 9))\n"
              << "  -o, --outfile <file>    Path and name of output file\n"
              << "  -f, --format <format>   File format to output to\n"
              << "  -l, --list              List supported file formats\n"
              << "  -d, --debug             If given, prints extra debug info during render\n"
              << "  -p, --printout          If set, copy of output in RGB triplets sent to screen\n"
              << "  -r, --resize <w,h>      Width, Height to resize image to\n"
              << "  -w, --width <w>         Width to create the initial image (overrides scene default)\n"
              << "  -s, --scale <factor>    Factor to scale image by (0.1 to 10)\n"
              << "  -h, --help              Show this help message\n";
}

int main(int argc, char* argv[]) {
    camera_options opt;
    int scene = 9;
    bool list_formats = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-h" || arg == "--help") {
            print_help(argv[0]);
            return 0;
        } else if (arg == "-l" || arg == "--list") {
            list_formats = true;
        } else if (arg == "-d" || arg == "--debug") {
            opt.debug = true;
        } else if (arg == "-p" || arg == "--printout") {
            opt.printout = true;
        } else if ((arg == "-c" || arg == "--scene") && i + 1 < argc) {
            scene = std::atoi(argv[++i]);
        } else if ((arg == "-o" || arg == "--outfile") && i + 1 < argc) {
            opt.outfile = argv[++i];
        } else if ((arg == "-f" || arg == "--format") && i + 1 < argc) {
            opt.format = argv[++i];
        } else if ((arg == "-w" || arg == "--width") && i + 1 < argc) {
            opt.width = std::atoi(argv[++i]);
        } else if ((arg == "-s" || arg == "--scale") && i + 1 < argc) {
            opt.is_scaled = true;
            opt.scale_fac = std::atof(argv[++i]);
            if (opt.scale_fac < 0.1) opt.scale_fac = 0.1;
            if (opt.scale_fac > 10.0) opt.scale_fac = 10.0;
        } else if ((arg == "-r" || arg == "--resize") && i + 1 < argc) {
            opt.is_resize = true;
            std::string res_str = argv[++i];
            auto comma_pos = res_str.find(',');
            if (comma_pos != std::string::npos) {
                opt.resize_w = std::atoi(res_str.substr(0, comma_pos).c_str());
                opt.resize_h = std::atoi(res_str.substr(comma_pos + 1).c_str());
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

    if (opt.is_scaled) {
        opt.is_resize = false;
    }

    if (!opt.outfile.empty()) {
        if (opt.format.empty()) {
            auto dot_pos = opt.outfile.find_last_of('.');
            if (dot_pos != std::string::npos) {
                std::string ext = opt.outfile.substr(dot_pos + 1);
                bool found = false;
                for (const auto& f : file_formats) {
                    if (f == ext) {
                        opt.format = ext;
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
            if (f == opt.format) {
                format_valid = true;
                break;
            }
        }
        if (!format_valid) {
            std::cerr << "Error: " << opt.format << " format not supported\n";
            return 1;
        }

        auto dot_pos = opt.outfile.find_last_of('.');
        if (dot_pos != std::string::npos) {
            opt.outfile = opt.outfile.substr(0, dot_pos) + "." + opt.format;
        } else {
            opt.outfile = opt.outfile + "." + opt.format;
        }
    }

    switch (scene) {
        case 1:  bouncing_spheres(opt);          break;
        case 2:  checkered_spheres(opt);         break;
        case 3:  earth(opt);                     break;
        case 4:  perlin_spheres(opt);            break;
        case 5:  quads(opt);                     break;
        case 6:  simple_light(opt);              break;
        case 7:  cornell_box(opt);               break;
        case 8:  cornell_smoke(opt);             break;
        case 9:  final_scene(800, 10000, 40, opt); break;
        default: final_scene(400,   250,  4, opt); break;
    }

    return 0;
}
