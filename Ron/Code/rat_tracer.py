import taichi as ti
import math

# 1. Initialize GPU acceleration
ti.init(arch=ti.cpu)

# Image dimensions
res_x, res_y = 800, 600
pixels = ti.Vector.field(
    3, dtype=ti.f32, shape=(res_x, res_y)
)

# 3D Sphere properties (Position X, Y, Z, Radius)
sphere_pos = ti.Vector([0.0, 0.0, -5.0])
sphere_radius = 1.5

# Light source position
light_pos = ti.Vector([-2.0, 5, -2.0])


@ti.func
def hit_sphere(ray_origin, ray_dir):
    """Calculates if a ray intersects the sphere. Returns distance t (-1.0 if miss)."""
    oc = ray_origin - sphere_pos
    a = ray_dir.dot(ray_dir)
    b = 2.0 * oc.dot(ray_dir)
    c = oc.dot(oc) - sphere_radius * sphere_radius
    discriminant = b * b - 4.0 * a * c

    t = -1.0
    if discriminant > 0.0:
        # Return the closest intersection point distance
        t = (-b - ti.sqrt(discriminant)) / (
            2.0 * a
        )
    return t


@ti.kernel
def render():
    # Automatically runs one thread per pixel in parallel on the GPU
    for x, y in pixels:
        # Normalize screen coordinates to [-1, 1] aspect-corrected window
        nx = (2.0 * x - res_x) / res_y
        ny = (2.0 * y - res_y) / res_y

        # Simple orthographic/perspective camera setups
        ray_origin = ti.Vector([0.0, 0.0, 0.0])
        ray_dir = ti.Vector(
            [nx, ny, -1.0]
        ).normalized()

        # Check intersection
        t = hit_sphere(ray_origin, ray_dir)

        if t > 0.0:
            # Calculate hit point and surface normal
            hit_point = ray_origin + t * ray_dir
            normal = (
                hit_point - sphere_pos
            ).normalized()

            # Lambertian (Diffuse) shading calculation
            light_dir = (
                light_pos - hit_point
            ).normalized()
            diffuse = ti.max(
                normal.dot(light_dir), 0.0
            )

            # Base sphere color mixed with light intensity
            sphere_color = ti.Vector(
                [0.5, 0.6, 0.9]
            )  # Cyan
            pixels[x, y] = sphere_color * (
                diffuse + 0.1
            )  # Added 0.1 ambient light
        else:
            # Background gradient color (sky effect)
            t_bg = 0.5 * (ray_dir.y + 1.0)
            pixels[x, y] = (
                1.0 - t_bg
            ) * ti.Vector(
                [1.0, 1.0, 1.0]
            ) + t_bg * ti.Vector(
                [0.5, 0.7, 1.0]
            )


# Create a GUI window to display the rendered canvas
gui = ti.GUI(
    "Taichi GPU Ray Tracer", res=(res_x, res_y)
)

while gui.running:
    render()
    gui.set_image(pixels)
    gui.show()
