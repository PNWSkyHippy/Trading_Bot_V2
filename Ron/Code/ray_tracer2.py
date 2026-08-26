import taichi as ti
import math

# 1. Initialize GPU acceleration
ti.init(arch=ti.cpu)

# Image dimensions
res_x, res_y = 800, 600
pixels = ti.Vector.field(
    3, dtype=ti.f32, shape=(res_x, res_y)
)

# Scene Objects: [Position X, Y, Z, Radius, Reflectivity, Type (0=Checker, 1=Solid)]
# Object 0: Large Mirror Sphere
s0_pos = ti.Vector([1.8, 0.0, -5.0])
s0_rad = 1.4
s0_refl = 1.0  # High reflectivity (80% mirror)
s0_type = 0  # Checkerboard texture

# Object 1: Small Shiny Green Sphere
s1_pos = ti.Vector([-1.5, -0.5, -4.0])
s1_rad = 0.9
s1_refl = (
    0.2  # Low reflectivity (30% shiny plastic)
)
s1_type = 1  # Solid green color

# Light source position
light_pos = ti.Vector([-2, 5.0, -2.0])


@ti.func
def hit_sphere(
    ray_origin, ray_dir, center, radius
):
    """Calculates ray-sphere intersection. Returns distance t (-1.0 if miss)."""
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
def get_sphere_texture_color(normal, obj_type):
    """Computes UV coordinates from the surface normal and returns a texture color."""
    color = ti.Vector([0.0, 0.0, 0.0])

    if obj_type == 1:
        # Solid Shiny Green
        color = ti.Vector([0.1, 0.8, 0.2])
    else:
        # Equirectangular UV mapping for a procedural checkerboard
        # u is longitude, v is latitude [0, 1]
        u = 0.5 + (
            ti.atan2(normal.z, normal.x)
            / (2.0 * math.pi)
        )
        v = 0.5 - (ti.asin(normal.y) / math.pi)

        # Scale up coordinates to create grid squares
        scale = 12.0
        check_x = ti.floor(u * scale)
        check_y = ti.floor(v * scale)

        # Alternate colors based on odd/even grid coordinates
        if int(check_x + check_y) % 2 == 0:
            color = ti.Vector(
                [0.9, 0.1, 0.1]
            )  # Red checks
        else:
            color = ti.Vector(
                [0.9, 0.9, 0.9]
            )  # White checks

    return color


@ti.kernel
def render():
    for x, y in pixels:
        # Camera Setup
        nx = (2.0 * x - res_x) / res_y
        ny = (2.0 * y - res_y) / res_y

        # Current ray tracking state
        ray_orig = ti.Vector([0.0, 0.0, 0.0])
        ray_dir = ti.Vector(
            [nx, ny, -1.0]
        ).normalized()

        # Color accumulation vars
        final_color = ti.Vector([0.0, 0.0, 0.0])
        reflection_throughput = ti.Vector(
            [1.0, 1.0, 1.0]
        )  # How much color passes back through bounces

        # Iterative Ray Loop (Max 3 bounces for deep reflections)
        for bounce in range(3):
            # Check intersections with both objects
            t0 = hit_sphere(
                ray_orig, ray_dir, s0_pos, s0_rad
            )
            t1 = hit_sphere(
                ray_orig, ray_dir, s1_pos, s1_rad
            )

            # Determine which object was hit closest to the ray origin
            hit_obj = -1
            t_closest = 1e9

            if 0.0 < t0 < t_closest:
                t_closest = t0
                hit_obj = 0
            if 0.0 < t1 < t_closest:
                t_closest = t1
                hit_obj = 1

            if hit_obj != -1:
                # Resolve surface coordinates
                obj_center = (
                    s0_pos
                    if hit_obj == 0
                    else s1_pos
                )
                obj_radius = (
                    s0_rad
                    if hit_obj == 0
                    else s1_rad
                )
                obj_refl = (
                    s0_refl
                    if hit_obj == 0
                    else s1_refl
                )
                obj_type = (
                    s0_type
                    if hit_obj == 0
                    else s1_type
                )

                # Calculate physical point and surface vector
                hit_point = (
                    ray_orig + t_closest * ray_dir
                )
                normal = (
                    hit_point - obj_center
                ).normalized()

                # Shading / Lighting Calculations
                light_dir = (
                    light_pos - hit_point
                ).normalized()
                diffuse_strength = ti.max(
                    normal.dot(light_dir), 0.0
                )

                # Get mapped texture color
                base_color = (
                    get_sphere_texture_color(
                        normal, obj_type
                    )
                )
                surface_shading = base_color * (
                    diffuse_strength + 0.1
                )

                # Mix current color into the frame based on remaining reflection strength
                final_color += (
                    surface_shading
                    * reflection_throughput
                    * (1.0 - obj_refl)
                )

                # Update throughput and prepare ray vectors for next bounce
                reflection_throughput *= obj_refl
                ray_dir = (
                    ray_dir
                    - 2.0
                    * ray_dir.dot(normal)
                    * normal
                )  # Standard reflection formula
                ray_orig = (
                    hit_point + normal * 0.001
                )  # Nudge forward to prevent self-intersection
            else:
                # Ray missed everything: Hit sky background gradient
                t_bg = 0.5 * (ray_dir.y + 1.0)
                sky_color = (
                    1.0 - t_bg
                ) * ti.Vector(
                    [1.0, 1.0, 1.0]
                ) + t_bg * ti.Vector(
                    [0.5, 0.7, 1.0]
                )
                final_color += (
                    sky_color
                    * reflection_throughput
                )
                break  # Sky absorbs ray; stop bouncing

        pixels[x, y] = final_color


# GUI visualization loop
gui = ti.GUI(
    "Taichi Reflections & Textures",
    res=(res_x, res_y),
)

while gui.running:
    render()
    gui.set_image(pixels)
    gui.show()
