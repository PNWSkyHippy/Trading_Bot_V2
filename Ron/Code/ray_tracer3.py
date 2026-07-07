import taichi as ti
import math
import numpy as np
from PIL import Image

# 1. Initialize GPU acceleration
ti.init(arch=ti.cpu)

# Screen Dimensions
res_x, res_y = 800, 600
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(res_x, res_y))

# ---------------------------------------------------------
# Load PNG Texture using Pillow and copy to Taichi Field
# ---------------------------------------------------------
try:
    img = Image.open("texture.png").convert("RGB")
except FileNotFoundError:
    # Fallback placeholder image if no local texture.png exists
    img = Image.new("RGB", (512, 512), color=(255, 200, 50))
    print("Warning: 'texture.png' not found. Generated a solid orange placeholder texture.")

tex_w, tex_h = img.size
img_data = np.array(img).astype(np.float32) / 255.0  # Normalize colors to [0.0, 1.0]

# Allocate texture memory space on the GPU
texture_field = ti.Vector.field(3, dtype=ti.f32, shape=(tex_w, tex_h))
texture_field.from_numpy(img_data)

# ---------------------------------------------------------
# Scene Configuration
# ---------------------------------------------------------
# Spheres: [Position X, Y, Z, Radius, Reflectivity, Type (0=PNG Map, 1=Shiny Solid)]
s0_pos, s0_rad, s0_refl, s0_type = ti.Vector([1.5, 0.0, -5.0]), 1.3, 0.4, 0
s1_pos, s1_rad, s1_refl, s1_type = ti.Vector([-1.5, -0.4, -4.5]), 1.0, 0.3, 1

# Multi-Light System (2 light sources with distinct colors and positions)
num_lights = 2
light_positions = ti.Vector.field(3, dtype=ti.f32, shape=num_lights)
light_colors = ti.Vector.field(3, dtype=ti.f32, shape=num_lights)

# Light 1: Cool Blue Main Light (Top Right)
light_positions[0] = ti.Vector([5.0, 5.0, -2.0])
light_colors[0] = ti.Vector([0.6, 0.8, 1.0]) * 1.2  # Brightness multiplier embedded

# Light 2: Warm Red-Orange Fill Light (Left Side)
light_positions[1] = ti.Vector([-6.0, 2.0, -3.0])
light_colors[1] = ti.Vector([1.0, 0.5, 0.3]) * 0.7  # Dimmer spread fill

@ti.func
def hit_sphere(ray_origin, ray_dir, center, radius):
    """Calculates ray-sphere intersection. Returns distance t (-1.0 if miss)."""
    oc = ray_origin - center
    a = ray_dir.dot(ray_dir)
    b = 2.0 * oc.dot(ray_dir)
    c = oc.dot(oc) - radius * radius
    discriminant = b * b - 4.0 * a * c
    t = -1.0
    if discriminant > 0.0:
        t = (-b - ti.sqrt(discriminant)) / (2.0 * a)
    return t

@ti.func
def sample_texture(normal):
    """Maps sphere surface normals into 2D UV pixels from loaded PNG image."""
    u = 0.5 + (ti.atan2(normal.z, normal.x) / (2.0 * math.pi))
    v = 0.5 - (ti.asin(normal.y) / math.pi)
    
    # Scale normalized [0,1] coordinates to match image pixel boundaries
    px = int(u * (tex_w - 1))
    py = int(v * (tex_h - 1))
    
    # Clamp pixel bounds safely
    px = ti.max(0, ti.min(px, tex_w - 1))
    py = ti.max(0, ti.min(py, tex_h - 1))
    
    return texture_field[px, py]

@ti.kernel
def render():
    for x, y in pixels:
        nx = (2.0 * x - res_x) / res_y
        ny = (2.0 * y - res_y) / res_y
        
        ray_orig = ti.Vector([0.0, 0.0, 0.0])
        ray_dir = ti.Vector([nx, ny, -1.0]).normalized()
        
        final_color = ti.Vector([0.0, 0.0, 0.0])
        reflection_throughput = ti.Vector([1.0, 1.0, 1.0])
        
        for bounce in range(3):
            t0 = hit_sphere(ray_orig, ray_dir, s0_pos, s0_rad)
            t1 = hit_sphere(ray_orig, ray_dir, s1_pos, s1_rad)
            
            hit_obj = -1
            t_closest = 1e9
            if 0.0 < t0 < t_closest: t_closest = t0; hit_obj = 0
            if 0.0 < t1 < t_closest: t_closest = t1; hit_obj = 1
                
            if hit_obj != -1:
                obj_center = s0_pos if hit_obj == 0 else s1_pos
                obj_radius = s0_rad if hit_obj == 0 else s1_rad
                obj_refl = s0_refl if hit_obj == 0 else s1_refl
                obj_type = s0_type if hit_obj == 0 else s1_type
                
                hit_point = ray_orig + t_closest * ray_dir
                normal = (hit_point - obj_center).normalized()
                
                # Determine Surface Base Color (PNG image sample vs Flat Shiny Purple)
                base_color = ti.Vector([0.5, 0.2, 0.8])
                if obj_type == 0:
                    base_color = sample_texture(normal)
                
                # Process Lighting Accumulation from ALL Light Sources
                illumination = ti.Vector([0.0, 0.0, 0.0])
                
                for l in range(num_lights):
                    light_dir = (light_positions[l] - hit_point).normalized()
                    light_dist = (light_positions[l] - hit_point).norm()
                    
                    # --- SHADOW RAY TESTING ---
                    # Offset ray origin slightly along normal vector to avoid local acne artifacts
                    shadow_orig = hit_point + normal * 0.002 
                    
                    # See if shadow ray hits the alternate sphere blocking this light
                    shadow_hit = -1
                    if hit_obj == 0:
                        if 0.0 < hit_sphere(shadow_orig, light_dir, s1_pos, s1_rad) < light_dist:
                            shadow_hit = 1
                    else:
                        if 0.0 < hit_sphere(shadow_orig, light_dir, s0_pos, s0_rad) < light_dist:
                            shadow_hit = 0
                    
                    # If shadow ray was not obstructed, add the diffuse color component
                    if shadow_hit == -1:
                        diffuse_strength = ti.max(normal.dot(light_dir), 0.0)
                        illumination += light_colors[l] * diffuse_strength
                
                # Add constant ambient lighting so shadowed faces aren't pitch black
                illumination += ti.Vector([0.08, 0.08, 0.08])
                surface_shading = base_color * illumination
                
                final_color += surface_shading * reflection_throughput * (1.0 - obj_refl)
                reflection_throughput *= obj_refl
                
                # Bounce Ray Setup
                ray_dir = (ray_dir - 2.0 * ray_dir.dot(normal) * normal).normalized()
                ray_orig = hit_point + normal * 0.002
            else:
                # Sky background
                t_bg = 0.5 * (ray_dir.y + 1.0)
                sky_color = (1.0 - t_bg) * ti.Vector([1.0, 1.0, 1.0]) + t_bg * ti.Vector([0.6, 0.7, 0.8])
                final_color += sky_color * reflection_throughput
                break
                
        pixels[x, y] = final_color

# GUI Loop Setup
gui = ti.GUI("Taichi PNG Textures & Multi-Shadows", res=(res_x, res_y))

while gui.running:
    render()
    gui.set_image(pixels)
    gui.show()
