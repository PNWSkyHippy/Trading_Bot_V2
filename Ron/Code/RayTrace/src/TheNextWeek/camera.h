#ifndef CAMERA_H
#define CAMERA_H
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

#include "hittable.h"
#include "material.h"

#include <iostream>
#include <fstream>
#include <vector>
#include <atomic>
#include <sstream>
#include <string>


class camera {
  public:
    std::string outfile           = "";
    bool   printout               = false;
    bool   debug                  = false;
    bool   is_scaled              = false;
    double scale_fac              = 1.0;
    bool   is_resize              = false;
    int    scaled_width           = 0;
    int    scaled_height          = 0;

    double aspect_ratio      = 1.0;  // Ratio of image width over height
    int    image_width       = 100;  // Rendered image width in pixel count
    int    samples_per_pixel = 10;   // Count of random samples for each pixel
    int    max_depth         = 10;   // Maximum number of ray bounces into scene
    color  background;               // Scene background color

    double vfov     = 90;              // Vertical view angle (field of view)
    point3 lookfrom = point3(0,0,0);   // Point camera is looking from
    point3 lookat   = point3(0,0,-1);  // Point camera is looking at
    vec3   vup      = vec3(0,1,0);     // Camera-relative "up" direction

    double defocus_angle = 0;  // Variation angle of rays through each pixel
    double focus_dist = 10;    // Distance from camera lookfrom point to plane of perfect focus

    void render(const hittable& world) {
        initialize();

        std::ofstream file_out;
        if (!outfile.empty()) {
            file_out.open(outfile);
            if (!file_out.is_open()) {
                std::cerr << "Error opening output file: " << outfile << "\n";
            } else {
                file_out << "P3\n" << image_width << ' ' << image_height << "\n255\n";
            }
        }

        if (printout) {
            std::cout << "P3\n" << image_width << ' ' << image_height << "\n255\n";
        }

        std::vector<std::string> scanlines(image_height);
        std::atomic<int> scanlines_completed{0};

        #pragma omp parallel for schedule(dynamic, 1)
        for (int j = 0; j < image_height; j++) {
            std::string row_str = "";
            for (int i = 0; i < image_width; i++) {
                color pixel_color(0,0,0);
                for (int sample = 0; sample < samples_per_pixel; sample++) {
                    ray r = get_ray(i, j);
                    pixel_color += ray_color(r, max_depth, world);
                }

                auto scaled = pixel_samples_scale * pixel_color;
                auto r = scaled.x();
                auto g = scaled.y();
                auto b = scaled.z();

                // Apply linear-to-gamma transform
                r = (r > 0) ? std::sqrt(r) : 0;
                g = (g > 0) ? std::sqrt(g) : 0;
                b = (b > 0) ? std::sqrt(b) : 0;

                static const interval intensity(0.000, 0.999);
                int rbyte = int(256 * intensity.clamp(r));
                int gbyte = int(256 * intensity.clamp(g));
                int bbyte = int(256 * intensity.clamp(b));

                std::string pixel_str = std::to_string(rbyte) + " " + std::to_string(gbyte) + " " + std::to_string(bbyte);
                if (i > 0) row_str += "  ";
                row_str += pixel_str;
            }
            scanlines[j] = row_str;

            if (printout) {
                #pragma omp critical
                {
                    std::cout << "LINE " << j << " " << row_str << "\n" << std::flush;
                }
            }

            if (debug) {
                int done = ++scanlines_completed;
                #pragma omp critical
                {
                    std::clog << "\rScanlines remaining: " << (image_height - done) << ' ' << std::flush;
                }
            }
        }

        for (int j = 0; j < image_height; j++) {
            if (file_out.is_open()) {
                file_out << scanlines[j] << "\n";
            }
        }

        if (file_out.is_open()) {
            file_out.close();
        }

        if (debug) {
            std::clog << "\rDone.                 \n";
        }
    }

  private:
    int    image_height;         // Rendered image height
    double pixel_samples_scale;  // Color scale factor for a sum of pixel samples
    point3 center;               // Camera center
    point3 pixel00_loc;          // Location of pixel 0, 0
    vec3   pixel_delta_u;        // Offset to pixel to the right
    vec3   pixel_delta_v;        // Offset to pixel below
    vec3   u, v, w;              // Camera frame basis vectors
    vec3   defocus_disk_u;       // Defocus disk horizontal radius
    vec3   defocus_disk_v;       // Defocus disk vertical radius

    void initialize() {
        image_height = int(image_width / aspect_ratio);
        image_height = (image_height < 1) ? 1 : image_height;

        pixel_samples_scale = 1.0 / samples_per_pixel;

        center = lookfrom;

        // Determine viewport dimensions.
        auto theta = degrees_to_radians(vfov);
        auto h = std::tan(theta/2);
        auto viewport_height = 2 * h * focus_dist;
        auto viewport_width = viewport_height * (double(image_width)/image_height);

        // Calculate the u,v,w unit basis vectors for the camera coordinate frame.
        w = unit_vector(lookfrom - lookat);
        u = unit_vector(cross(vup, w));
        v = cross(w, u);

        // Calculate the vectors across the horizontal and down the vertical viewport edges.
        vec3 viewport_u = viewport_width * u;    // Vector across viewport horizontal edge
        vec3 viewport_v = viewport_height * -v;  // Vector down viewport vertical edge

        // Calculate the horizontal and vertical delta vectors from pixel to pixel.
        pixel_delta_u = viewport_u / image_width;
        pixel_delta_v = viewport_v / image_height;

        // Calculate the location of the upper left pixel.
        auto viewport_upper_left = center - (focus_dist * w) - viewport_u/2 - viewport_v/2;
        pixel00_loc = viewport_upper_left + 0.5 * (pixel_delta_u + pixel_delta_v);

        // Calculate the camera defocus disk basis vectors.
        auto defocus_radius = focus_dist * std::tan(degrees_to_radians(defocus_angle / 2));
        defocus_disk_u = u * defocus_radius;
        defocus_disk_v = v * defocus_radius;
    }

    ray get_ray(int i, int j) const {
        // Construct a camera ray originating from the defocus disk and directed at a randomly
        // sampled point around the pixel location i, j.

        auto offset = sample_square();
        auto pixel_sample = pixel00_loc
                          + ((i + offset.x()) * pixel_delta_u)
                          + ((j + offset.y()) * pixel_delta_v);

        auto ray_origin = (defocus_angle <= 0) ? center : defocus_disk_sample();
        auto ray_direction = pixel_sample - ray_origin;
        auto ray_time = random_double();

        return ray(ray_origin, ray_direction, ray_time);
    }

    vec3 sample_square() const {
        // Returns the vector to a random point in the [-.5,-.5]-[+.5,+.5] unit square.
        return vec3(random_double() - 0.5, random_double() - 0.5, 0);
    }

    vec3 sample_disk(double radius) const {
        // Returns a random point in the unit (radius 0.5) disk centered at the origin.
        return radius * random_in_unit_disk();
    }

    point3 defocus_disk_sample() const {
        // Returns a random point in the camera defocus disk.
        auto p = random_in_unit_disk();
        return center + (p[0] * defocus_disk_u) + (p[1] * defocus_disk_v);
    }

    color ray_color(const ray& r, int depth, const hittable& world) const {
        // If we've exceeded the ray bounce limit, no more light is gathered.
        if (depth <= 0)
            return color(0,0,0);

        hit_record rec;

        // If the ray hits nothing, return the background color.
        if (!world.hit(r, interval(0.001, infinity), rec))
            return background;

        ray scattered;
        color attenuation;
        color color_from_emission = rec.mat->emitted(rec.u, rec.v, rec.p);

        if (!rec.mat->scatter(r, rec, attenuation, scattered))
            return color_from_emission;

        color color_from_scatter = attenuation * ray_color(scattered, depth-1, world);

        return color_from_emission + color_from_scatter;
    }
};


#endif
