import taichi as ti
import math
import numpy as np
from PIL import Image

# 1. Initialize GPU acceleration
ti.init(arch=ti.cpu)

# Restored the reliable resolution from your stable script
res_x, res_y = 800, 600
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(res_x, res_y))

# ---------------------------------------------------------
# Load PNG Texture Map
# ---------------------------------------------------------
try:
    img = Image.open("texture.png").convert("RGB")
except FileNotFoundError:
    img = Image.new("RGB", (512, 512), color=(255, 200, 50))
    print("Warning: 'texture.png' not found. Using orange placeholder.")

tex_w, tex_h = img.size
img_data = np.array(img).astype(np.float32) / 255.0
texture_field = ti.Vector.field(3, dtype=ti.f32, shape=(tex_w, tex_h))
texture_field.from_numpy(img_data)

# ---------------------------------------------------------
# Stable Scene Constants 
# ---------------------------------------------------------
planet_pos = ti.Vector([0.0, 0.0, -6.0])
planet_rad = 1.6
planet_refl = 0.3

ring_inner = 2.2
ring_outer = 4.2

@ti.func
def hit_sphere(ray_origin, ray_dir, center, radius):
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
def hit_ring(ray_origin, ray_dir):
    t = -1.0
    if ti.abs(ray_dir.y) > 1e-4:
        t = (planet_pos.y - ray_origin.y) / ray_dir.y
        if t > 0.0:
            hit_p = ray_origin + t * ray_dir
            dx = hit_p.x - planet_pos.x
            dz = hit_p.z - planet_pos.z
            dist_to_center = ti.sqrt(dx * dx + dz * dz)
            if dist_to_center < ring_inner or dist_to_center > ring_outer:
                t = -1.0
    return t

@ti.func
def sample_texture(normal):
    u = 0.5 + (ti.atan2(normal.z, normal.x) / (2.0 * math.pi))
    v = 0.5 - (ti.asin(normal.y) / math.pi)
    px = ti.max(0, ti.min(int(u * (tex_w - 1)), tex_w - 1))
    py = ti.max(0, ti.min(int(v * (tex_h - 1)), tex_h - 1))
    return texture_field[px, py]

@ti.func
def sample_ring_density(ray_origin, ray_dir, t_ring):
    hit_p = ray_origin + t_ring * ray_dir
    dx = hit_p.x - planet_pos.x
    dz = hit_p.z - planet_pos.z
    dist = ti.sqrt(dx * dx + dz * dz)
    density = ti.sin(dist * 25.0) * 0.5 + 0.5
    ring_color = ti.Vector([0.8, 0.6, 0.7]) * density
    return ring_color, density

@ti.func
def pseudo_random_stars(direction):
    scale = direction * 150.0
    noise = ti.sin(scale.x) * ti.cos(scale.y) * 12345.67
    noise = noise - ti.floor(noise)
    star = 0.0
    if noise > 0.994:
        star = 1.0
    return ti.Vector([star, star, star])

# ---------------------------------------------------------
# Restored Stable Kernel Blueprint
# ---------------------------------------------------------
@ti.kernel
def render(c_pos: ti.types.vector(3, ti.f32), c_lookat: ti.types.vector(3, ti.f32), moons_packed: ti.types.vector(3, ti.f32), sun_pos: ti.types.vector(3, ti.f32)):
    forward = (c_lookat - c_pos).normalized()
    world_up = ti.Vector([0.0, 1.0, 0.0])
    right = forward.cross(world_up).normalized()
    up = right.cross(forward).normalized()

    # Unpack the two moon vectors inside the kernel registers
    m1_pos = ti.Vector([moons_packed.x, moons_packed.y, moons_packed.z])
    # The fast second inner moon scales dynamically based on angular shifts
    m2_pos = ti.Vector([-moons_packed.x * 0.6, -moons_packed.y, moons_packed.z * 0.6])

    for x, y in pixels:
        nx = (2.0 * x - res_x) / res_y
        ny = (2.0 * y - res_y) / res_y
        
        ray_orig = c_pos
        ray_dir = (forward + (nx * right) + (ny * up)).normalized()
        
        final_color = ti.Vector([0.0, 0.0, 0.0])
        reflection_throughput = ti.Vector([1.0, 1.0, 1.0])
        
        oc_halo = ray_orig - planet_pos
        b_halo = oc_halo.dot(ray_dir)
        c_halo = oc_halo.dot(oc_halo) - (planet_rad * 1.15) * (planet_rad * 1.15)
        disc_halo = b_halo * b_halo - c_halo
        
        for bounce in range(3):
            t0 = hit_sphere(ray_orig, ray_dir, planet_pos, planet_rad)
            t1 = hit_sphere(ray_orig, ray_dir, m1_pos, 0.4) # Moon 1 radius 0.4
            t2 = hit_sphere(ray_orig, ray_dir, m2_pos, 0.22) # Moon 2 radius 0.22
            t3 = hit_ring(ray_orig, ray_dir)
            
            hit_obj = -1
            t_closest = 1e9
            if 0.0 < t0 < t_closest: t_closest = t0; hit_obj = 0
            if 0.0 < t1 < t_closest: t_closest = t1; hit_obj = 1
            if 0.0 < t2 < t_closest: t_closest = t2; hit_obj = 2
            if 0.0 < t3 < t_closest: t_closest = t3; hit_obj = 3
                
            if hit_obj != -1:
                if hit_obj == 3:
                    # Rings Render channel
                    ring_col, opacity = sample_ring_density(ray_orig, ray_dir, t_closest)
                    hit_point = ray_orig + t_closest * ray_dir
                    light_dir = (sun_pos - hit_point).normalized()
                    light_dist = (sun_pos - hit_point).norm()
                    
                    shadow_orig = hit_point + ti.Vector([0.0, 1.0, 0.0]) * 0.002
                    shadow_hit = False
                    if 0.0 < hit_sphere(shadow_orig, light_dir, planet_pos, planet_rad) < light_dist: shadow_hit = True
                    
                    illumination = ti.Vector([0.02, 0.02, 0.04])
                    if not shadow_hit:
                        illumination += (ti.Vector([1.0, 0.95, 0.85]) * 1.5) * ti.abs(ti.Vector([0.0, 1.0, 0.0]).dot(light_dir))
                    
                    final_color += ring_col * illumination * reflection_throughput * opacity
                    reflection_throughput *= (1.0 - opacity)
                    ray_orig = hit_point + ray_dir * 0.002 
                    
                else:
                    # Sphere Shading channel
                 
                 
                    light_dir = (sun_pos - hit_point).normalized()
                    light_dist = (sun_pos - hit_point).norm()
                    
                    shadow_orig = hit_point + normal * 0.002
                    shadow_hit = False
                    
                    if hit_obj == 0:
                        if 0.0 < hit_sphere(shadow_orig, light_dir, m1_pos, 0.4) < light_dist: shadow_hit = True
                        if 0.0 < hit_sphere(shadow_orig, light_dir, m2_pos, 0.22) < light_dist: shadow_hit = True
                        t_ring_shadow = hit_ring(shadow_orig, light_dir)
                        if 0.0 < t_ring_shadow < light_dist:
                            _, ring_opacity = sample_ring_density(shadow_orig, light_dir, t_ring_shadow)
                            if ring_opacity > 0.4: shadow_hit = True
                    else:
                        if 0.0 < hit_sphere(shadow_orig, light_dir, planet_pos, planet_rad) < light_dist: shadow_hit = True
                    
                    illumination = ti.Vector([0.02, 0.02, 0.04])
                    if not shadow_hit:
                        illumination += (ti.Vector([1.0, 0.95, 0.85]) * 1.5) * ti.max(normal.dot(light_dir), 0.0)
                    
                    final_color += base_color * illumination * reflection_throughput * (1.0 - refl)
                    reflection_throughput *= refl
                    
                    ray_dir = (ray_dir - 2.0 * ray_dir.dot(normal) * normal).normalized()
                    ray_orig = hit_point + normal * 0.002
            else:
                space_bg = pseudo_random_stars(ray_dir)
                if disc_halo > 0.0 and t0 < 0.0:
                    glow_factor = ti.max(0.0, ray_dir.dot((sun_pos - planet_pos).normalized())) 
                    space_bg += ti.Vector([0.2, 0.5, 1.0]) * glow_factor * 0.4
                    
                final_color += space_bg * reflection_throughput
                break
                
        pixels[x, y] = final_color

# ---------------------------------------------------------
# Interactive Main Timeline Loop
# ---------------------------------------------------------
time_clock = 0.0
gui = ti.GUI("Fixed Architecture Engine", res=(res_x, res_y))

while gui.running:
    mouse_x, mouse_y = gui.get_cursor_pos()
    angle = mouse_x * 2.0 * math.pi
    distance = 4.0 + (mouse_y * 8.0) 
    
    cam_x = planet_pos.x + math.sin(angle) * distance
    cam_z = planet_pos.z + math.cos(angle) * distance
    cam_y = planet_pos.y + (mouse_y * 4.0 - 2.0) 
    
    c_pos_vec = ti.Vector([cam_x, cam_y, cam_z])
    c_target_vec = ti.Vector([planet_pos.x, planet_pos.y, planet_pos.z])

    # Advance clock timeline
    time_clock += 0.015

    # Moon 1 Math Track (Outer wide trail)
    m1_radius = 3.2
    m1_x = planet_pos.x + math.sin(time_clock) * m1_radius
    m1_z = planet_pos.z + math.cos(time_clock) * m1_radius
    m1_y = planet_pos.y + math.sin(time_clock * 0.5) * 0.3
    
    # Pack the position data into a single vector argument
