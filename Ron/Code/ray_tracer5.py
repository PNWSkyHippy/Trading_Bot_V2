import taichi as ti
import math
import numpy as np
from PIL import Image

# 1. Initialize GPU acceleration
ti.init(arch=ti.cpu)

res_x, res_y = 800, 600
pixels = ti.Vector.field(
    3, dtype=ti.f32, shape=(res_x, res_y)
)

# ---------------------------------------------------------
# Load PNG Texture
# ---------------------------------------------------------
try:
    img = Image.open("texture.png").convert("RGB")
except FileNotFoundError:
    img = Image.new(
        "RGB", (512, 512), color=(255, 200, 50)
    )
    print(
        "Warning: 'texture.png' not found. Using orange placeholder."
    )

tex_w, tex_h = img.size
img_data = (
    np.array(img).astype(np.float32) / 255.0
)
texture_field = ti.Vector.field(
    3, dtype=ti.f32, shape=(tex_w, tex_h)
)
texture_field.from_numpy(img_data)

# ---------------------------------------------------------
# Deep Space Scene Variables
# ---------------------------------------------------------
planet_pos = ti.Vector([0.0, 0.0, -6.0])
planet_rad = 1.6
planet_refl = 0.1

moon_rad = 0.4
moon_refl = 0.5

star_pos = ti.Vector([15.0, 8.0, 2.0])
star_color = ti.Vector([1.0, 0.95, 0.85]) * 1.5


@ti.func
def hit_sphere(
    ray_origin, ray_dir, center, radius
):
    oc = ray_origin - center
    a = ray_dir.dot(ray_dir)
    b = 2.0 * oc.dot(ray_dir)
    c = oc.dot(oc) - radius * radius
    discriminant = b * b - 4.0 * a * c
    t = -1.0
    if discriminant > 0.0:
        t = (-b - ti.sqrt(discriminant)) / (
            2.0 * a
        )
    return t


@ti.func
def sample_texture(normal):
    u = 0.5 + (
        ti.atan2(normal.z, normal.x)
        / (2.0 * math.pi)
    )
    v = 0.5 - (ti.asin(normal.y) / math.pi)
    px = ti.max(
        0, ti.min(int(u * (tex_w - 1)), tex_w - 1)
    )
    py = ti.max(
        0, ti.min(int(v * (tex_h - 1)), tex_h - 1)
    )
    return texture_field[px, py]


# ---------------------------------------------------------
# Space Ray Tracer Engine
# ---------------------------------------------------------
@ti.kernel
def render(
    c_pos: ti.types.vector(3, ti.f32),
    c_lookat: ti.types.vector(3, ti.f32),
    m_pos: ti.types.vector(3, ti.f32),
):
    forward = (c_lookat - c_pos).normalized()
    world_up = ti.Vector([0.0, 1.0, 0.0])
    right = forward.cross(world_up).normalized()
    up = right.cross(forward).normalized()

    for x, y in pixels:
        nx = (2.0 * x - res_x) / res_y
        ny = (2.0 * y - res_y) / res_y

        ray_orig = c_pos
        ray_dir = (
            forward + (nx * right) + (ny * up)
        ).normalized()

        final_color = ti.Vector([0.0, 0.0, 0.0])
        reflection_throughput = ti.Vector(
            [1.0, 1.0, 1.0]
        )

        oc_halo = ray_orig - planet_pos
        b_halo = oc_halo.dot(ray_dir)
        c_halo = oc_halo.dot(oc_halo) - (
            planet_rad * 1.15
        ) * (planet_rad * 1.15)
        disc_halo = b_halo * b_halo - c_halo

        for bounce in range(3):
            t0 = hit_sphere(
                ray_orig,
                ray_dir,
                planet_pos,
                planet_rad,
            )
            t1 = hit_sphere(
                ray_orig, ray_dir, m_pos, moon_rad
            )

            hit_obj = -1
            t_closest = 1e9
            if 0.0 < t0 < t_closest:
                t_closest = t0
                hit_obj = 0
            if 0.0 < t1 < t_closest:
                t_closest = t1
                hit_obj = 1

            if hit_obj != -1:
                obj_center = (
                    planet_pos
                    if hit_obj == 0
                    else m_pos
                )
                obj_radius = (
                    planet_rad
                    if hit_obj == 0
                    else moon_rad
                )
                obj_refl = (
                    planet_refl
                    if hit_obj == 0
                    else moon_refl
                )

                hit_point = (
                    ray_orig + t_closest * ray_dir
                )
                normal = (
                    hit_point - obj_center
                ).normalized()

                base_color = ti.Vector(
                    [0.1, 0.4, 0.8]
                )
                if hit_obj == 0:
                    base_color = sample_texture(
                        normal
                    )

                light_dir = (
                    star_pos - hit_point
                ).normalized()
                light_dist = (
                    star_pos - hit_point
                ).norm()

                shadow_orig = (
                    hit_point + normal * 0.002
                )
                shadow_hit = False
                if hit_obj == 0:
                    if (
                        0.0
                        < hit_sphere(
                            shadow_orig,
                            light_dir,
                            m_pos,
                            moon_rad,
                        )
                        < light_dist
                    ):
                        shadow_hit = True
                else:
                    if (
                        0.0
                        < hit_sphere(
                            shadow_orig,
                            light_dir,
                            planet_pos,
                            planet_rad,
                        )
                        < light_dist
                    ):
                        shadow_hit = True

                illumination = ti.Vector(
                    [0.02, 0.02, 0.04]
                )
                if not shadow_hit:
                    illumination += (
                        star_color
                        * ti.max(
                            normal.dot(light_dir),
                            0.0,
                        )
                    )

                final_color += (
                    base_color
                    * illumination
                    * reflection_throughput
                    * (1.0 - obj_refl)
                )
                reflection_throughput *= obj_refl

                ray_dir = (
                    ray_dir
                    - 2.0
                    * ray_dir.dot(normal)
                    * normal
                ).normalized()
                ray_orig = (
                    hit_point + normal * 0.002
                )
            else:
                nebula_t = 0.5 * (ray_dir.y + 1.0)
                space_bg = (
                    1.0 - nebula_t
                ) * ti.Vector(
                    [0.02, 0.01, 0.04]
                ) + nebula_t * ti.Vector(
                    [0.0, 0.0, 0.02]
                )

                if disc_halo > 0.0 and t0 < 0.0:
                    glow_factor = ti.max(
                        0.0,
                        ray_dir.dot(
                            (
                                star_pos
                                - planet_pos
                            ).normalized()
                        ),
                    )
                    space_bg += (
                        ti.Vector([0.2, 0.5, 1.0])
                        * glow_factor
                        * 0.4
                    )

                final_color += (
                    space_bg
                    * reflection_throughput
                )
                break

        pixels[x, y] = final_color


# ---------------------------------------------------------
# FIXED Interactive Space Controller Loop
# ---------------------------------------------------------
# Set camera position at origin, looking directly down -Z toward the planet
camera_pos = np.array(
    [0.0, 0.0, 0.0], dtype=np.float32
)
camera_target = np.array(
    [0.0, 0.0, -6.0], dtype=np.float32
)
move_speed = 0.1
time_clock = 0.0

gui = ti.GUI(
    "Fixed Controls - Space Engine",
    res=(res_x, res_y),
)

print("\n--- Controls Fixed! ---")
print(
    "W / S : Move forward / backward along look direction"
)
print("A / D : Strafe left / right sideways")
print("SPACE : Fly Up vertically")
print("SHIFT : Fly Down vertically\n")

while gui.running:
    # 1. Dynamically compute the camera's true movement vectors in Python
    forward = camera_target - camera_pos
    # Normalize forward vector safely
    forward_norm = forward / np.linalg.norm(
        forward
    )

    # Calculate right vector (perpendicular to forward and world up)
    right_vec = np.cross(
        forward_norm,
        np.array(
            [0.0, 1.0, 0.0], dtype=np.float32
        ),
    )
    right_norm = right_vec / np.linalg.norm(
        right_vec
    )

    # 2. Check key inputs and modify vectors along their real directions
    if gui.is_pressed("w"):
        camera_pos += forward_norm * move_speed
        camera_target += forward_norm * move_speed
    if gui.is_pressed("s"):
        camera_pos -= forward_norm * move_speed
        camera_target -= forward_norm * move_speed
    if gui.is_pressed("a"):
        camera_pos -= right_norm * move_speed
        camera_target -= right_norm * move_speed
    if gui.is_pressed("d"):
        camera_pos += right_norm * move_speed
        camera_target += right_norm * move_speed
    if gui.is_pressed(gui.SPACE):
        camera_pos[1] += move_speed
        camera_target[1] += move_speed
    if gui.is_pressed(gui.SHIFT):
        camera_pos[1] -= move_speed
        camera_target[1] -= move_speed

    # 3. Update Orbital Physics for the Moon
    time_clock += 0.02
    orbit_radius = 2.8
    moon_x = (
        planet_pos.x
        + math.sin(time_clock) * orbit_radius
    )
    moon_z = (
        planet_pos.z
        + math.cos(time_clock) * orbit_radius
    )
    moon_y = (
        planet_pos.y
        + math.sin(time_clock * 0.5) * 0.4
    )
    current_moon_pos = ti.Vector(
        [moon_x, moon_y, moon_z]
    )

    # Pass precise 3-element float vectors directly into the Taichi rendering kernel
    c_pos_vec = ti.Vector(
        [
            camera_pos[0],
            camera_pos[1],
            camera_pos[2],
        ]
    )
    c_target_vec = ti.Vector(
        [
            camera_target[0],
            camera_target[1],
            camera_target[2],
        ]
    )

    render(
        c_pos_vec, c_target_vec, current_moon_pos
    )

    gui.set_image(pixels)
    gui.show()
