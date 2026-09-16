#include "TheNextWeek/rtweekend.h"

#include "TheNextWeek/bvh.h"
#include "TheNextWeek/camera.h"
#include "TheNextWeek/constant_medium.h"
#include "TheNextWeek/hittable.h"
#include "TheNextWeek/hittable_list.h"
#include "TheNextWeek/material.h"
#include "TheNextWeek/quad.h"
#include "TheNextWeek/sphere.h"
#include "TheNextWeek/texture.h"

#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

const std::vector<std::string> file_formats = {
    "bmp", "gif", "ico",
    "jpg", "pcx", "png",
    "ppm", "tga", "tif"
};

struct extra_light_options {
    point3 position = point3(0, 0, 0);
    double power = 1.0;
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
    bool has_camera_position = false;
    point3 camera_position = point3(0, 0, 0);
    bool has_look_at = false;
    point3 look_at = point3(0, 0, 0);
    bool has_vfov = false;
    double vfov = 0.0;
    std::vector<extra_light_options> extra_lights;
};

bool parse_number_list(const std::string& text, std::vector<double>& values) {
    values.clear();
    std::istringstream stream(text);
    std::string field;
    while (std::getline(stream, field, ',')) {
        try {
            size_t consumed = 0;
            const double value = std::stod(field, &consumed);
            if (consumed != field.size()) return false;
            values.push_back(value);
        } catch (...) {
            return false;
        }
    }
    return !values.empty();
}

bool parse_point3(const std::string& text, point3& point) {
    std::vector<double> values;
    if (!parse_number_list(text, values) || values.size() != 3) return false;
    point = point3(values[0], values[1], values[2]);
    return true;
}

bool parse_extra_light(const std::string& text, extra_light_options& light) {
    std::vector<double> values;
    if (!parse_number_list(text, values) || values.size() != 4) return false;
    if (values[3] < 0.0 || values[3] > 1.0) return false;
    light.position = point3(values[0], values[1], values[2]);
    light.power = values[3];
    return true;
}

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
    if (opt.has_camera_position) cam.lookfrom = opt.camera_position;
    if (opt.has_look_at) cam.lookat = opt.look_at;
    if (opt.has_vfov) cam.vfov = opt.vfov;
}

void apply_extra_lights(hittable_list& world, const camera_options& opt) {
    for (const auto& light : opt.extra_lights) {
        if (light.power <= 0.0) continue;
        const double emission = 15.0 * light.power;
        auto material = make_shared<diffuse_light>(color(emission, emission, emission));
        world.add(make_shared<sphere>(light.position, 0.25, material));
    }
}

void render_scene(hittable_list& world, camera& cam, const camera_options& opt) {
    apply_options(cam, opt);
    apply_extra_lights(world, opt);
    cam.render(world);
}

void book1_default_scene(const camera_options& opt) {
    hittable_list world;

    auto ground_material = make_shared<lambertian>(color(0.5, 0.5, 0.5));
    world.add(make_shared<sphere>(point3(0, -1000, 0), 1000, ground_material));

    for (int a = -11; a < 11; a++) {
        for (int b = -11; b < 11; b++) {
            auto choose_mat = random_double();
            point3 center(a + 0.9 * random_double(), 0.2, b + 0.9 * random_double());

            if ((center - point3(4, 0.2, 0)).length() > 0.9) {
                shared_ptr<material> sphere_material;

                if (choose_mat < 0.8) {
                    auto albedo = color::random() * color::random();
                    sphere_material = make_shared<lambertian>(albedo);
                    world.add(make_shared<sphere>(center, 0.2, sphere_material));
                } else if (choose_mat < 0.95) {
                    auto albedo = color::random(0.5, 1);
                    auto fuzz = random_double(0, 0.5);
                    sphere_material = make_shared<metal>(albedo, fuzz);
                    world.add(make_shared<sphere>(center, 0.2, sphere_material));
                } else {
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
    cam.aspect_ratio = 16.0 / 9.0;
    cam.image_width = (opt.width > 0) ? opt.width : 1200;
    cam.samples_per_pixel = 10;
    cam.max_depth = 20;
    cam.background = color(0.70, 0.80, 1.00);
    cam.vfov = 20;
    cam.lookfrom = point3(13, 2, 3);
    cam.lookat = point3(0, 0, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0.6;
    cam.focus_dist = 10.0;
    render_scene(world, cam, opt);
}

void bouncing_spheres(const camera_options& opt) {
    hittable_list world;

    auto checker = make_shared<checker_texture>(0.32, color(0.2, 0.3, 0.1), color(0.9, 0.9, 0.9));
    world.add(make_shared<sphere>(point3(0, -1000, 0), 1000, make_shared<lambertian>(checker)));

    for (int a = -11; a < 11; a++) {
        for (int b = -11; b < 11; b++) {
            auto choose_mat = random_double();
            point3 center(a + 0.9 * random_double(), 0.2, b + 0.9 * random_double());

            if ((center - point3(4, 0.2, 0)).length() > 0.9) {
                if (choose_mat < 0.8) {
                    auto albedo = color::random() * color::random();
                    auto sphere_material = make_shared<lambertian>(albedo);
                    auto center2 = center + vec3(0, random_double(0, 0.5), 0);
                    world.add(make_shared<sphere>(center, center2, 0.2, sphere_material));
                } else if (choose_mat < 0.95) {
                    auto albedo = color::random(0.5, 1);
                    auto fuzz = random_double(0, 0.5);
                    auto sphere_material = make_shared<metal>(albedo, fuzz);
                    world.add(make_shared<sphere>(center, 0.2, sphere_material));
                } else {
                    auto sphere_material = make_shared<dielectric>(1.5);
                    world.add(make_shared<sphere>(center, 0.2, sphere_material));
                }
            }
        }
    }

    world.add(make_shared<sphere>(point3(0, 1, 0), 1.0, make_shared<dielectric>(1.5)));
    world.add(make_shared<sphere>(point3(-4, 1, 0), 1.0, make_shared<lambertian>(color(0.4, 0.2, 0.1))));
    world.add(make_shared<sphere>(point3(4, 1, 0), 1.0, make_shared<metal>(color(0.7, 0.6, 0.5), 0.0)));

    world = hittable_list(make_shared<bvh_node>(world));

    camera cam;
    cam.aspect_ratio = 16.0 / 9.0;
    cam.image_width = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth = 50;
    cam.background = color(0.70, 0.80, 1.00);
    cam.vfov = 20;
    cam.lookfrom = point3(13, 2, 3);
    cam.lookat = point3(0, 0, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0.6;
    cam.focus_dist = 10.0;
    render_scene(world, cam, opt);
}

void checkered_spheres(const camera_options& opt) {
    hittable_list world;
    auto checker = make_shared<checker_texture>(0.32, color(0.2, 0.3, 0.1), color(0.9, 0.9, 0.9));
    world.add(make_shared<sphere>(point3(0, -10, 0), 10, make_shared<lambertian>(checker)));
    world.add(make_shared<sphere>(point3(0, 10, 0), 10, make_shared<lambertian>(checker)));

    camera cam;
    cam.aspect_ratio = 16.0 / 9.0;
    cam.image_width = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth = 50;
    cam.background = color(0.70, 0.80, 1.00);
    cam.vfov = 20;
    cam.lookfrom = point3(13, 2, 3);
    cam.lookat = point3(0, 0, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    render_scene(world, cam, opt);
}

void earth_scene(const camera_options& opt) {
    auto earth_texture = make_shared<image_texture>("earthmap.jpg");
    auto earth_surface = make_shared<lambertian>(earth_texture);
    auto globe = make_shared<sphere>(point3(0, 0, 0), 2, earth_surface);

    camera cam;
    cam.aspect_ratio = 16.0 / 9.0;
    cam.image_width = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth = 50;
    cam.background = color(0.70, 0.80, 1.00);
    cam.vfov = 20;
    cam.lookfrom = point3(0, 0, 12);
    cam.lookat = point3(0, 0, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    hittable_list world;
    world.add(globe);
    render_scene(world, cam, opt);
}

void perlin_spheres(const camera_options& opt) {
    hittable_list world;
    auto pertext = make_shared<noise_texture>(4);
    world.add(make_shared<sphere>(point3(0, -1000, 0), 1000, make_shared<lambertian>(pertext)));
    world.add(make_shared<sphere>(point3(0, 2, 0), 2, make_shared<lambertian>(pertext)));

    camera cam;
    cam.aspect_ratio = 16.0 / 9.0;
    cam.image_width = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth = 50;
    cam.background = color(0.70, 0.80, 1.00);
    cam.vfov = 20;
    cam.lookfrom = point3(13, 2, 3);
    cam.lookat = point3(0, 0, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    render_scene(world, cam, opt);
}

void quads_scene(const camera_options& opt) {
    hittable_list world;

    auto left_red = make_shared<lambertian>(color(1.0, 0.2, 0.2));
    auto back_green = make_shared<lambertian>(color(0.2, 1.0, 0.2));
    auto right_blue = make_shared<lambertian>(color(0.2, 0.2, 1.0));
    auto upper_orange = make_shared<lambertian>(color(1.0, 0.5, 0.0));
    auto lower_teal = make_shared<lambertian>(color(0.2, 0.8, 0.8));

    world.add(make_shared<quad>(point3(-3, -2, 5), vec3(0, 0, -4), vec3(0, 4, 0), left_red));
    world.add(make_shared<quad>(point3(-2, -2, 0), vec3(4, 0, 0), vec3(0, 4, 0), back_green));
    world.add(make_shared<quad>(point3(3, -2, 1), vec3(0, 0, 4), vec3(0, 4, 0), right_blue));
    world.add(make_shared<quad>(point3(-2, 3, 1), vec3(4, 0, 0), vec3(0, 0, 4), upper_orange));
    world.add(make_shared<quad>(point3(-2, -3, 5), vec3(4, 0, 0), vec3(0, 0, -4), lower_teal));

    camera cam;
    cam.aspect_ratio = 1.0;
    cam.image_width = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth = 50;
    cam.background = color(0.70, 0.80, 1.00);
    cam.vfov = 80;
    cam.lookfrom = point3(0, 0, 9);
    cam.lookat = point3(0, 0, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    render_scene(world, cam, opt);
}

void simple_light_scene(const camera_options& opt) {
    hittable_list world;
    auto pertext = make_shared<noise_texture>(4);
    world.add(make_shared<sphere>(point3(0, -1000, 0), 1000, make_shared<lambertian>(pertext)));
    world.add(make_shared<sphere>(point3(0, 2, 0), 2, make_shared<lambertian>(pertext)));

    auto difflight = make_shared<diffuse_light>(color(4, 4, 4));
    world.add(make_shared<sphere>(point3(0, 7, 0), 2, difflight));
    world.add(make_shared<quad>(point3(3, 1, -2), vec3(2, 0, 0), vec3(0, 2, 0), difflight));

    camera cam;
    cam.aspect_ratio = 16.0 / 9.0;
    cam.image_width = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth = 50;
    cam.background = color(0, 0, 0);
    cam.vfov = 20;
    cam.lookfrom = point3(26, 3, 6);
    cam.lookat = point3(0, 2, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    render_scene(world, cam, opt);
}

void cornell_box_scene(const camera_options& opt) {
    hittable_list world;

    auto red = make_shared<lambertian>(color(0.65, 0.05, 0.05));
    auto white = make_shared<lambertian>(color(0.73, 0.73, 0.73));
    auto green = make_shared<lambertian>(color(0.12, 0.45, 0.15));
    auto light = make_shared<diffuse_light>(color(15, 15, 15));

    world.add(make_shared<quad>(point3(555, 0, 0), vec3(0, 555, 0), vec3(0, 0, 555), green));
    world.add(make_shared<quad>(point3(0, 0, 0), vec3(0, 555, 0), vec3(0, 0, 555), red));
    world.add(make_shared<quad>(point3(343, 554, 332), vec3(-130, 0, 0), vec3(0, 0, -105), light));
    world.add(make_shared<quad>(point3(0, 0, 0), vec3(555, 0, 0), vec3(0, 0, 555), white));
    world.add(make_shared<quad>(point3(555, 555, 555), vec3(-555, 0, 0), vec3(0, 0, -555), white));
    world.add(make_shared<quad>(point3(0, 0, 555), vec3(555, 0, 0), vec3(0, 555, 0), white));

    shared_ptr<hittable> box1 = box(point3(0, 0, 0), point3(165, 330, 165), white);
    box1 = make_shared<rotate_y>(box1, 15);
    box1 = make_shared<translate>(box1, vec3(265, 0, 295));
    world.add(box1);

    shared_ptr<hittable> box2 = box(point3(0, 0, 0), point3(165, 165, 165), white);
    box2 = make_shared<rotate_y>(box2, -18);
    box2 = make_shared<translate>(box2, vec3(130, 0, 65));
    world.add(box2);

    camera cam;
    cam.aspect_ratio = 1.0;
    cam.image_width = 600;
    cam.samples_per_pixel = 200;
    cam.max_depth = 50;
    cam.background = color(0, 0, 0);
    cam.vfov = 40;
    cam.lookfrom = point3(278, 278, -800);
    cam.lookat = point3(278, 278, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    render_scene(world, cam, opt);
}

void cornell_smoke_scene(const camera_options& opt) {
    hittable_list world;

    auto red = make_shared<lambertian>(color(0.65, 0.05, 0.05));
    auto white = make_shared<lambertian>(color(0.73, 0.73, 0.73));
    auto green = make_shared<lambertian>(color(0.12, 0.45, 0.15));
    auto light = make_shared<diffuse_light>(color(7, 7, 7));

    world.add(make_shared<quad>(point3(555, 0, 0), vec3(0, 555, 0), vec3(0, 0, 555), green));
    world.add(make_shared<quad>(point3(0, 0, 0), vec3(0, 555, 0), vec3(0, 0, 555), red));
    world.add(make_shared<quad>(point3(113, 554, 127), vec3(330, 0, 0), vec3(0, 0, 305), light));
    world.add(make_shared<quad>(point3(0, 555, 0), vec3(555, 0, 0), vec3(0, 0, 555), white));
    world.add(make_shared<quad>(point3(0, 0, 0), vec3(555, 0, 0), vec3(0, 0, 555), white));
    world.add(make_shared<quad>(point3(0, 0, 555), vec3(555, 0, 0), vec3(0, 0, 555), white));

    shared_ptr<hittable> box1 = box(point3(0, 0, 0), point3(165, 330, 165), white);
    box1 = make_shared<rotate_y>(box1, 15);
    box1 = make_shared<translate>(box1, vec3(265, 0, 295));

    shared_ptr<hittable> box2 = box(point3(0, 0, 0), point3(165, 165, 165), white);
    box2 = make_shared<rotate_y>(box2, -18);
    box2 = make_shared<translate>(box2, vec3(130, 0, 65));

    world.add(make_shared<constant_medium>(box1, 0.01, color(0, 0, 0)));
    world.add(make_shared<constant_medium>(box2, 0.01, color(1, 1, 1)));

    camera cam;
    cam.aspect_ratio = 1.0;
    cam.image_width = 600;
    cam.samples_per_pixel = 200;
    cam.max_depth = 50;
    cam.background = color(0, 0, 0);
    cam.vfov = 40;
    cam.lookfrom = point3(278, 278, -800);
    cam.lookat = point3(278, 278, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    render_scene(world, cam, opt);
}

void final_scene(const camera_options& opt, int image_width = 800, int samples_per_pixel = 10000, int max_depth = 40) {
    hittable_list boxes1;
    auto ground = make_shared<lambertian>(color(0.48, 0.83, 0.53));

    int boxes_per_side = 20;
    for (int i = 0; i < boxes_per_side; i++) {
        for (int j = 0; j < boxes_per_side; j++) {
            auto w = 100.0;
            auto x0 = -1000.0 + i * w;
            auto z0 = -1000.0 + j * w;
            auto y0 = 0.0;
            auto x1 = x0 + w;
            auto y1 = random_double(1, 101);
            auto z1 = z0 + w;

            boxes1.add(box(point3(x0, y0, z0), point3(x1, y1, z1), ground));
        }
    }

    hittable_list world;
    world.add(make_shared<bvh_node>(boxes1));

    auto light = make_shared<diffuse_light>(color(7, 7, 7));
    world.add(make_shared<quad>(point3(123, 554, 147), vec3(300, 0, 0), vec3(0, 0, 265), light));

    auto center1 = point3(400, 400, 200);
    auto center2 = center1 + vec3(30, 0, 0);
    auto sphere_material = make_shared<lambertian>(color(0.7, 0.3, 0.1));
    world.add(make_shared<sphere>(center1, center2, 50, sphere_material));

    world.add(make_shared<sphere>(point3(260, 150, 45), 50, make_shared<dielectric>(1.5)));
    world.add(make_shared<sphere>(point3(0, 150, 145), 50, make_shared<metal>(color(0.8, 0.8, 0.9), 1.0)));

    auto boundary = make_shared<sphere>(point3(360, 150, 145), 70, make_shared<dielectric>(1.5));
    world.add(boundary);
    world.add(make_shared<constant_medium>(boundary, 0.2, color(0.2, 0.4, 0.9)));
    boundary = make_shared<sphere>(point3(0, 0, 0), 5000, make_shared<dielectric>(1.5));
    world.add(make_shared<constant_medium>(boundary, .0001, color(1, 1, 1)));

    auto emat = make_shared<lambertian>(make_shared<image_texture>("earthmap.jpg"));
    world.add(make_shared<sphere>(point3(400, 200, 400), 100, emat));
    auto pertext = make_shared<noise_texture>(0.2);
    world.add(make_shared<sphere>(point3(220, 280, 300), 80, make_shared<lambertian>(pertext)));

    hittable_list boxes2;
    auto white = make_shared<lambertian>(color(.73, .73, .73));
    int ns = 1000;
    for (int j = 0; j < ns; j++) {
        boxes2.add(make_shared<sphere>(point3::random(0, 165), 10, white));
    }

    world.add(make_shared<translate>(
        make_shared<rotate_y>(
            make_shared<bvh_node>(boxes2), 15),
        vec3(-100, 270, 395)
    ));

    camera cam;
    cam.aspect_ratio = 1.0;
    cam.image_width = image_width;
    cam.samples_per_pixel = samples_per_pixel;
    cam.max_depth = max_depth;
    cam.background = color(0, 0, 0);
    cam.vfov = 40;
    cam.lookfrom = point3(478, 278, -600);
    cam.lookat = point3(278, 278, 0);
    cam.vup = vec3(0, 1, 0);
    cam.defocus_angle = 0;
    render_scene(world, cam, opt);
}

void print_help(const char* prog) {
    std::cout << "Usage: " << prog << " [options]\n\n"
              << "  -b, --book <1|2|3>      Book to render (1: In One Weekend, 2: The Next Week, 3: The Rest of Your Life)\n"
              << "  -c, --scene <n>         Scene selector (Book 2: 1-9; Book 1/3: default single scene)\n"
              << "  -o, --outfile <file>    Path and name of output file\n"
              << "  -f, --format <format>   File format to output to\n"
              << "  -l, --list              List supported file formats\n"
              << "  -d, --debug             If given, prints extra debug info during render\n"
              << "  -p, --printout          If set, copy of output in RGB triplets sent to screen\n"
              << "  -r, --resize <w,h>      Width, Height to resize image to\n"
              << "  -w, --width <w>         Width to create the initial image (overrides scene default)\n"
              << "  -s, --scale <factor>    Factor to scale image by (0.1 to 10)\n"
              << "      --camera <x,y,z>    Override the scene camera position\n"
              << "      --look-at <x,y,z>   Override the point the camera looks at\n"
              << "      --vfov <degrees>    Override vertical field of view (0 < degrees < 180)\n"
              << "      --light <x,y,z,p>   Add a white light; p is brightness from 0.0 to 1.0\n"
              << "  -h, --help              Show this help message\n";
}

int main(int argc, char* argv[]) {
    camera_options opt;
    int book = 2;
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
        } else if ((arg == "-b" || arg == "--book") && i + 1 < argc) {
            book = std::atoi(argv[++i]);
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
        } else if (arg == "--camera" && i + 1 < argc) {
            if (!parse_point3(argv[++i], opt.camera_position)) {
                std::cerr << "Error: --camera requires x,y,z\n";
                return 2;
            }
            opt.has_camera_position = true;
        } else if (arg == "--look-at" && i + 1 < argc) {
            if (!parse_point3(argv[++i], opt.look_at)) {
                std::cerr << "Error: --look-at requires x,y,z\n";
                return 2;
            }
            opt.has_look_at = true;
        } else if (arg == "--vfov" && i + 1 < argc) {
            try {
                opt.vfov = std::stod(argv[++i]);
            } catch (...) {
                std::cerr << "Error: --vfov requires a number between 0 and 180\n";
                return 2;
            }
            if (opt.vfov <= 0.0 || opt.vfov >= 180.0) {
                std::cerr << "Error: --vfov must be between 0 and 180\n";
                return 2;
            }
            opt.has_vfov = true;
        } else if (arg == "--light" && i + 1 < argc) {
            extra_light_options light;
            if (!parse_extra_light(argv[++i], light)) {
                std::cerr << "Error: --light requires x,y,z,p where p is 0.0 to 1.0\n";
                return 2;
            }
            opt.extra_lights.push_back(light);
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
        std::cout << "\n";
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

    switch (book) {
        case 1:
            book1_default_scene(opt);
            break;
        case 2:
            switch (scene) {
                case 1: bouncing_spheres(opt); break;
                case 2: checkered_spheres(opt); break;
                case 3: earth_scene(opt); break;
                case 4: perlin_spheres(opt); break;
                case 5: quads_scene(opt); break;
                case 6: simple_light_scene(opt); break;
                case 7: cornell_box_scene(opt); break;
                case 8: cornell_smoke_scene(opt); break;
                case 9:
                default:
                    final_scene(opt, 800, 10000, 40);
                    break;
            }
            break;
        case 3:
        default:
            book1_default_scene(opt);
            break;
    }

    return 0;
}
