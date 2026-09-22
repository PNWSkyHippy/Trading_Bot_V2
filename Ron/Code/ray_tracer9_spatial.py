"""
===============================================================================
RAY_TRACER 9: SPATIAL AUDIO & 6-DOF ASTRAL FLIGHT ENGINE (MAC & PC OPTIMIZED)
===============================================================================
Controls (100% Silent & Zero-Beep on macOS):
  - [Left-Click Drag]       : Steer & Aim 360° Pitch/Yaw (Look anywhere)
  - [Right-Click (Hold)]    : Thrust FORWARD into space!
  - [Middle-Click / S]      : Thrust BACKWARD
  - [SHIFT (Hold)]          : Turbo Speed Boost (Silent modifier key!)
  - [Arrow Keys / WASD]     : Optional keyboard flight
  - [ESC]                   : Exit

Spatial Audio (Dual-Channel 3D System):
  - Channel 1: Dynamic 3D Planetary Drone (Deep cosmic hum that pans with camera and scales with distance)
  - Channel 2: Real-time 3D Doppler Meteor Whoosh (Screams past ears with binaural panning)
===============================================================================
"""

import math
import random
import time
import threading
import numpy as np
from PIL import Image

import taichi as ti

# Auto-select best GPU backend (Metal on Mac, CUDA/Vulkan on PC, or CPU fallback)
try:
    ti.init(arch=ti.gpu)
except Exception:
    ti.init(arch=ti.cpu)

# ---------------------------------------------------------------------------
# Resolution & Display Field
# ---------------------------------------------------------------------------
res_x, res_y = 800, 600
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(res_x, res_y))

# ---------------------------------------------------------------------------
# Load Planet PNG Texture Map
# ---------------------------------------------------------------------------
try:
    img = Image.open("texture.png").convert("RGB")
except FileNotFoundError:
    img = Image.new("RGB", (512, 512), color=(255, 180, 50))

tex_w, tex_h = img.size
img_data = np.array(img).astype(np.float32) / 255.0
texture_field = ti.Vector.field(3, dtype=ti.f32, shape=(tex_w, tex_h))
texture_field.from_numpy(img_data)

# ---------------------------------------------------------------------------
# Scene Constants
# ---------------------------------------------------------------------------
planet_pos = ti.Vector([0.0, 0.0, -6.0])
planet_rad = 1.6
planet_refl = 0.3
ring_inner = 2.2
ring_outer = 4.2


# ---------------------------------------------------------------------------
# Ray Tracing GPU Functions
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Main Ray Tracing Render Kernel
# ---------------------------------------------------------------------------
@ti.kernel
def render(
    c_pos: ti.types.vector(3, ti.f32),
    c_forward: ti.types.vector(3, ti.f32),
    c_right: ti.types.vector(3, ti.f32),
    c_up: ti.types.vector(3, ti.f32),
    moons_packed: ti.types.vector(3, ti.f32),
    sun_pos: ti.types.vector(3, ti.f32),
    meteor_pos: ti.types.vector(3, ti.f32),
    meteor_active: ti.f32,
):
    m1_pos = ti.Vector([moons_packed.x, moons_packed.y, moons_packed.z])
    m2_pos = ti.Vector([-moons_packed.x * 0.6, -moons_packed.y, moons_packed.z * 0.6])

    for x, y in pixels:
        nx = (2.0 * x - res_x) / res_y
        ny = (2.0 * y - res_y) / res_y

        ray_orig = c_pos
        ray_dir = (c_forward + (nx * c_right) + (ny * c_up)).normalized()

        final_color = ti.Vector([0.0, 0.0, 0.0])
        reflection_throughput = ti.Vector([1.0, 1.0, 1.0])

        oc_halo = ray_orig - planet_pos
        b_halo = oc_halo.dot(ray_dir)
        c_halo = oc_halo.dot(oc_halo) - (planet_rad * 1.15) * (planet_rad * 1.15)
        disc_halo = b_halo * b_halo - c_halo

        for bounce in range(3):
            t0 = hit_sphere(ray_orig, ray_dir, planet_pos, planet_rad)
            t1 = hit_sphere(ray_orig, ray_dir, m1_pos, 0.4)
            t2 = hit_sphere(ray_orig, ray_dir, m2_pos, 0.22)
            t3 = hit_ring(ray_orig, ray_dir)

            hit_obj = -1
            t_closest = 1e9
            if 0.0 < t0 < t_closest:
                t_closest = t0
                hit_obj = 0
            if 0.0 < t1 < t_closest:
                t_closest = t1
                hit_obj = 1
            if 0.0 < t2 < t_closest:
                t_closest = t2
                hit_obj = 2
            if 0.0 < t3 < t_closest:
                t_closest = t3
                hit_obj = 3

            if hit_obj != -1:
                if hit_obj == 3:
                    # Rings Shading Channel
                    ring_col, opacity = sample_ring_density(
                        ray_orig, ray_dir, t_closest
                    )
                    hit_point = ray_orig + t_closest * ray_dir
                    light_dir = (sun_pos - hit_point).normalized()
                    light_dist = (sun_pos - hit_point).norm()

                    shadow_orig = hit_point + ti.Vector([0.0, 1.0, 0.0]) * 0.002
                    shadow_hit = False
                    if (
                        0.0
                        < hit_sphere(shadow_orig, light_dir, planet_pos, planet_rad)
                        < light_dist
                    ):
                        shadow_hit = True

                    illumination = ti.Vector([0.02, 0.02, 0.04])
                    if not shadow_hit:
                        illumination += (ti.Vector([1.0, 0.95, 0.85]) * 1.5) * ti.abs(
                            ti.Vector([0.0, 1.0, 0.0]).dot(light_dir)
                        )

                    final_color += (
                        ring_col * illumination * reflection_throughput * opacity
                    )
                    reflection_throughput *= 1.0 - opacity
                    ray_orig = hit_point + ray_dir * 0.002

                else:
                    # Spheres (Planet / Moons) Shading Channel
                    obj_center = (
                        planet_pos
                        if hit_obj == 0
                        else (m1_pos if hit_obj == 1 else m2_pos)
                    )
                    obj_radius = (
                        planet_rad if hit_obj == 0 else (0.4 if hit_obj == 1 else 0.22)
                    )
                    obj_refl = planet_refl if hit_obj == 0 else 0.5

                    hit_point = ray_orig + t_closest * ray_dir
                    normal = (hit_point - obj_center).normalized()
                    base_color = (
                        sample_texture(normal)
                        if hit_obj == 0
                        else ti.Vector([0.6, 0.6, 0.65])
                    )
                    refl = obj_refl

                    light_dir = (sun_pos - hit_point).normalized()
                    light_dist = (sun_pos - hit_point).norm()

                    shadow_orig = hit_point + normal * 0.002
                    shadow_hit = False

                    if hit_obj == 0:
                        if (
                            0.0
                            < hit_sphere(shadow_orig, light_dir, m1_pos, 0.4)
                            < light_dist
                        ):
                            shadow_hit = True
                        if (
                            0.0
                            < hit_sphere(shadow_orig, light_dir, m2_pos, 0.22)
                            < light_dist
                        ):
                            shadow_hit = True
                        t_ring_shadow = hit_ring(shadow_orig, light_dir)
                        if 0.0 < t_ring_shadow < light_dist:
                            _, ring_opacity = sample_ring_density(
                                shadow_orig, light_dir, t_ring_shadow
                            )
                            if ring_opacity > 0.4:
                                shadow_hit = True
                    else:
                        if (
                            0.0
                            < hit_sphere(shadow_orig, light_dir, planet_pos, planet_rad)
                            < light_dist
                        ):
                            shadow_hit = True

                    illumination = ti.Vector([0.02, 0.02, 0.04])
                    if not shadow_hit:
                        illumination += (ti.Vector([1.0, 0.95, 0.85]) * 1.5) * ti.max(
                            normal.dot(light_dir), 0.0
                        )

                    final_color += (
                        base_color * illumination * reflection_throughput * (1.0 - refl)
                    )
                    reflection_throughput *= refl

                    ray_dir = (
                        ray_dir - 2.0 * ray_dir.dot(normal) * normal
                    ).normalized()
                    ray_orig = hit_point + normal * 0.002
            else:
                space_bg = pseudo_random_stars(ray_dir)
                if disc_halo > 0.0 and t0 < 0.0:
                    glow_factor = ti.max(
                        0.0, ray_dir.dot((sun_pos - planet_pos).normalized())
                    )
                    space_bg += ti.Vector([0.2, 0.5, 1.0]) * glow_factor * 0.4

                final_color += space_bg * reflection_throughput
                break

        # -------------------------------------------------------------
        # Volumetric Glowing Meteor Head & Plasma Trail Glow
        # -------------------------------------------------------------
        if meteor_active > 0.0:
            m_oc = ray_orig - meteor_pos
            m_proj = -m_oc.dot(ray_dir)
            if m_proj > 0.0:
                closest_p = ray_orig + m_proj * ray_dir
                dist_to_meteor = (closest_p - meteor_pos).norm()
                if dist_to_meteor < 1.5:
                    glow_strength = ti.exp(-dist_to_meteor * 2.8) * meteor_active
                    final_color += ti.Vector([1.0, 0.75, 0.35]) * glow_strength * 4.5

        pixels[x, y] = final_color


# ---------------------------------------------------------------------------
# Dual-Channel 3D Spatial Audio Engine (Planetary Drone + Meteor Whoosh)
# ---------------------------------------------------------------------------
class SpatialAudioEngine:
    def __init__(self):
        self.sample_rate = 44100
        self.has_audio = False
        self.drone_channel = None
        self.meteor_channel = None

        try:
            import pygame

            pygame.mixer.init(
                frequency=self.sample_rate, size=-16, channels=2, buffer=1024
            )
            pygame.mixer.set_num_channels(8)
            self.has_audio = True

            self.meteor_channel = pygame.mixer.Channel(0)
            self.drone_channel = pygame.mixer.Channel(1)

            # Synthesize seamless 3-second warm cosmic drone loop
            duration = 3.0
            num_samples = int(self.sample_rate * duration)
            t = np.linspace(
                0.0, duration, num_samples, endpoint=False, dtype=np.float32
            )

            # Harmonics: 55 Hz (Fundamental), 110 Hz (Octave), 165 Hz (Fifth)
            w1 = np.sin(2.0 * np.pi * 55.0 * t) * 0.5
            w2 = np.sin(2.0 * np.pi * 110.0 * t) * 0.3
            w3 = np.sin(2.0 * np.pi * 165.0 * t) * 0.2
            drone_wave = (w1 + w2 + w3) * 0.4

            # Create clean looping stereo sound
            stereo_drone = np.column_stack(
                (drone_wave * 32767, drone_wave * 32767)
            ).astype(np.int16)
            self.drone_sound = pygame.sndarray.make_sound(stereo_drone)

            # Start infinite loop on drone channel
            self.drone_channel.play(self.drone_sound, loops=-1)
            self.drone_channel.set_volume(0.2, 0.2)
            print(
                "🔊 3D Spatial Audio: [Dual-Channel Mixer Active] Planetary Hum & Meteors Live!"
            )
        except Exception as e:
            print(f"⚠️ Audio initialization bypassed: {e}")

    def update_drone(self, listener_pos, listener_right):
        """Modulates the planetary drone volume and panning based on listener position."""
        if not self.has_audio or not self.drone_channel:
            return

        rel_pos = np.array([0.0, 0.0, -6.0]) - listener_pos
        dist = float(np.linalg.norm(rel_pos))
        if dist > 0.01:
            dir_to_planet = rel_pos / dist
            pan = float(np.clip(np.dot(dir_to_planet, listener_right), -1.0, 1.0))

            # Volume decreases as you fly away into deep space
            vol = float(np.clip(2.5 / (1.0 + dist * 0.25), 0.05, 0.45))
            vol_l = vol * float(np.sqrt(max(0.0, (1.0 - pan) * 0.5)))
            vol_r = vol * float(np.sqrt(max(0.0, (1.0 + pan) * 0.5)))

            self.drone_channel.set_volume(vol_l, vol_r)

    def play_meteor_whoosh(self, start_pos, vel, listener_pos, listener_right):
        """Synthesizes and plays a smooth, cinematic 3D Doppler plasma whoosh."""
        if not self.has_audio or not self.meteor_channel:
            return

        def _synth_and_play():
            import pygame

            duration = 2.4
            num_samples = int(self.sample_rate * duration)
            t = np.linspace(0.0, duration, num_samples, dtype=np.float32)

            pos_t = start_pos[:, None] + vel[:, None] * t[None, :]
            rel_pos = pos_t - listener_pos[:, None]
            dists = np.linalg.norm(rel_pos, axis=0)
            dists = np.maximum(dists, 0.5)

            # Volume Gaussian envelope centered at closest approach
            min_idx = np.argmin(dists)
            t_closest = t[min_idx]
            vol_curve = np.exp(-((t - t_closest) ** 2) / (2.0 * (0.35**2)))
            vol_curve *= np.clip(3.5 / dists, 0.0, 1.0)

            # Binaural Panning: Left (-1) to Right (+1) over time
            dirs = rel_pos / dists[None, :]
            pans = np.sum(dirs * listener_right[:, None], axis=0)
            vol_left = vol_curve * np.sqrt(np.maximum(0.0, (1.0 - pans) * 0.5))
            vol_right = vol_curve * np.sqrt(np.maximum(0.0, (1.0 + pans) * 0.5))

            # Doppler Frequency Drop: High approach (380 Hz) -> Low departure (120 Hz)
            freq_curve = 380.0 - (260.0 / (1.0 + np.exp(-(t - t_closest) * 8.0)))
            phase = np.cumsum(2.0 * np.pi * freq_curve / self.sample_rate)

            # Warm Organic Noise + Harmonic Tone (Smooth Jet / Meteor Roar)
            noise = np.random.uniform(-0.35, 0.35, num_samples).astype(np.float32)
            wave = np.sin(phase) * 0.5 + noise * 0.5

            left_channel = np.clip(wave * vol_left, -1.0, 1.0) * 32767
            right_channel = np.clip(wave * vol_right, -1.0, 1.0) * 32767
            stereo = np.column_stack((left_channel, right_channel)).astype(np.int16)

            sound = pygame.sndarray.make_sound(stereo)
            self.meteor_channel.play(sound)

        threading.Thread(target=_synth_and_play, daemon=True).start()

    def stop(self):
        if self.has_audio:
            try:
                import pygame

                pygame.mixer.stop()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# 3D Meteor Spawner / Tracker (Frequent Streaks)
# ---------------------------------------------------------------------------
class MeteorSpawner:
    def __init__(self, audio_engine):
        self.audio = audio_engine
        self.active = False
        self.pos = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.vel = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.lifetime = 0.0
        self.next_spawn_time = time.time() + 1.2

    def update(self, dt, listener_pos, listener_right):
        now = time.time()
        if not self.active and now > self.next_spawn_time:
            # Spawn a meteor streaking across the visible viewport
            spawn_side = random.choice(["left", "right", "top", "front"])
            if spawn_side == "left":
                self.pos = np.array(
                    [-11.0, random.uniform(-1.0, 3.0), random.uniform(-6.0, 2.0)],
                    dtype=np.float32,
                )
                self.vel = np.array(
                    [
                        random.uniform(10.0, 15.0),
                        random.uniform(-1.0, 1.0),
                        random.uniform(-3.0, 3.0),
                    ],
                    dtype=np.float32,
                )
            elif spawn_side == "right":
                self.pos = np.array(
                    [11.0, random.uniform(-1.0, 3.0), random.uniform(-6.0, 2.0)],
                    dtype=np.float32,
                )
                self.vel = np.array(
                    [
                        random.uniform(-15.0, -10.0),
                        random.uniform(-1.0, 1.0),
                        random.uniform(-3.0, 3.0),
                    ],
                    dtype=np.float32,
                )
            elif spawn_side == "top":
                self.pos = np.array(
                    [random.uniform(-5.0, 5.0), 8.0, random.uniform(-8.0, 0.0)],
                    dtype=np.float32,
                )
                self.vel = np.array(
                    [
                        random.uniform(-3.0, 3.0),
                        random.uniform(-14.0, -9.0),
                        random.uniform(-4.0, 4.0),
                    ],
                    dtype=np.float32,
                )
            else:
                self.pos = np.array(
                    [random.uniform(-5.0, 5.0), random.uniform(-1.0, 3.0), -14.0],
                    dtype=np.float32,
                )
                self.vel = np.array(
                    [
                        random.uniform(-2.0, 2.0),
                        random.uniform(-1.0, 2.0),
                        random.uniform(11.0, 16.0),
                    ],
                    dtype=np.float32,
                )

            self.active = True
            self.lifetime = 0.0
            # Play dedicated smooth 3D Doppler audio for this meteor!
            self.audio.play_meteor_whoosh(
                self.pos, self.vel, listener_pos, listener_right
            )
            self.next_spawn_time = now + random.uniform(2.5, 4.5)

        if self.active:
            self.pos += self.vel * dt
            self.lifetime += dt
            if self.lifetime > 2.4 or np.linalg.norm(self.pos) > 28.0:
                self.active = False


# ---------------------------------------------------------------------------
# Main Interactive Loop (Zero-Beep Mouse Flight + Spatial Audio)
# ---------------------------------------------------------------------------
def main():
    audio = SpatialAudioEngine()
    meteor = MeteorSpawner(audio)

    # 6-DOF Camera State
    cam_pos = np.array([0.0, 0.8, 5.5], dtype=np.float32)
    cam_yaw = 0.0
    cam_pitch = 0.0
    base_speed = 7.0

    gui = ti.GUI(
        "Ray-Tracer 9: 6-DOF Space Flight & 3D Spatial Audio", res=(res_x, res_y)
    )

    is_left_dragging = False
    is_right_thrusting = False
    last_mouse_pos = gui.get_cursor_pos()

    time_clock = 0.0
    last_frame_time = time.time()
    fps = 60.0

    print("\n" + "=" * 70)
    print("🚀 100% SILENT ASTRAL MOUSE CONTROLS (Zero Mac Alert Beeps):")
    print("  [Left-Click Drag]     : Steer & Aim 360° Pitch/Yaw")
    print("  [Right-Click (Hold)]  : Thrust FORWARD into space!")
    print("  [Middle-Click / S]    : Thrust BACKWARD")
    print("  [SHIFT (Hold)]        : Turbo Thrust Boost!")
    print("  [ESC]                 : Exit")
    print("=" * 70 + "\n")

    while gui.running:
        now = time.time()
        dt = max(0.001, min(now - last_frame_time, 0.1))
        last_frame_time = now
        fps = 0.9 * fps + 0.1 * (1.0 / dt)

        # -------------------------------------------------------------
        # 1. Mouse Button State Tracking (Completely Silent on macOS)
        # -------------------------------------------------------------
        cur_mouse = gui.get_cursor_pos()
        for e in gui.get_events(ti.GUI.PRESS):
            if e.key == ti.GUI.ESCAPE:
                gui.running = False
            elif e.key == ti.GUI.LMB:
                is_left_dragging = True
                last_mouse_pos = cur_mouse
            elif e.key == ti.GUI.RMB:
                is_right_thrusting = True

        for e in gui.get_events(ti.GUI.RELEASE):
            if e.key == ti.GUI.LMB:
                is_left_dragging = False
            elif e.key == ti.GUI.RMB:
                is_right_thrusting = False

        # Steer view when dragging left click
        if is_left_dragging:
            dx = cur_mouse[0] - last_mouse_pos[0]
            dy = cur_mouse[1] - last_mouse_pos[1]
            sensitivity = 3.0
            cam_yaw += dx * sensitivity
            cam_pitch = float(
                np.clip(cam_pitch + dy * sensitivity, -math.pi * 0.48, math.pi * 0.48)
            )
            last_mouse_pos = cur_mouse

        # -------------------------------------------------------------
        # 2. Camera Orientation Vectors
        # -------------------------------------------------------------
        forward = np.array(
            [
                math.sin(cam_yaw) * math.cos(cam_pitch),
                math.sin(cam_pitch),
                -math.cos(cam_yaw) * math.cos(cam_pitch),
            ],
            dtype=np.float32,
        )
        forward = forward / np.linalg.norm(forward)

        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        right = np.cross(forward, world_up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        # -------------------------------------------------------------
        # 3. Speed & Direction Calculation
        # -------------------------------------------------------------
        is_turbo = gui.is_pressed(ti.GUI.SHIFT)
        current_speed = base_speed * (2.2 if is_turbo else 1.0)

        move_dir = np.zeros(3, dtype=np.float32)

        # Silent Mouse Thrust
        if is_right_thrusting or gui.is_pressed(ti.GUI.MMB):
            move_dir += forward

        # Optional Keyboard Controls
        if gui.is_pressed(ti.GUI.UP, "w", "W"):
            move_dir += forward
        if gui.is_pressed(ti.GUI.DOWN, "s", "S"):
            move_dir -= forward
        if gui.is_pressed(ti.GUI.LEFT, "a", "A"):
            move_dir -= right
        if gui.is_pressed(ti.GUI.RIGHT, "d", "D"):
            move_dir += right
        if gui.is_pressed(ti.GUI.SPACE, "r", "R"):
            move_dir += world_up
        if gui.is_pressed("f", "F"):
            move_dir -= world_up

        if np.linalg.norm(move_dir) > 0.01:
            move_dir = move_dir / np.linalg.norm(move_dir)
            cam_pos += move_dir * current_speed * dt

        # -------------------------------------------------------------
        # 4. Simulation Step (Meteors & Moons)
        # -------------------------------------------------------------
        time_clock += dt
        meteor.update(dt, cam_pos, right)

        # Update 3D Planetary Drone Position & Panning
        audio.update_drone(cam_pos, right)

        m1_radius = 3.2
        m1_x = planet_pos[0] + math.sin(time_clock * 0.8) * m1_radius
        m1_z = planet_pos[2] + math.cos(time_clock * 0.8) * m1_radius
        m1_y = planet_pos[1] + math.sin(time_clock * 0.4) * 0.3
        moons_packed_vec = ti.Vector([m1_x, m1_y, m1_z])
        sun_pos_vec = ti.Vector([15.0, 8.0, 2.0])

        # -------------------------------------------------------------
        # 5. GPU Ray Tracing Pass
        # -------------------------------------------------------------
        c_pos_vec = ti.Vector([cam_pos[0], cam_pos[1], cam_pos[2]])
        c_forward_vec = ti.Vector([forward[0], forward[1], forward[2]])
        c_right_vec = ti.Vector([right[0], right[1], right[2]])
        c_up_vec = ti.Vector([up[0], up[1], up[2]])
        meteor_pos_vec = ti.Vector([meteor.pos[0], meteor.pos[1], meteor.pos[2]])
        meteor_active_val = 1.0 if meteor.active else 0.0

        render(
            c_pos_vec,
            c_forward_vec,
            c_right_vec,
            c_up_vec,
            moons_packed_vec,
            sun_pos_vec,
            meteor_pos_vec,
            meteor_active_val,
        )

        # -------------------------------------------------------------
        # 6. Render HUD & Blit
        # -------------------------------------------------------------
        gui.set_image(pixels)
        gui.text(
            content=f"FPS: {fps:.1f}", pos=(0.04, 0.95), color=0x00FF00, font_size=18
        )
        gui.text(
            content="[Left Drag] Steer  [Right Hold] Thrust Forward  [SHIFT] Turbo",
            pos=(0.04, 0.06),
            color=0x88CCFF,
            font_size=14,
        )
        if meteor.active:
            gui.text(
                content="☄️ METEOR INCOMING!",
                pos=(0.36, 0.92),
                color=0xFFAA00,
                font_size=18,
            )

        gui.show()

    audio.stop()


if __name__ == "__main__":
    main()
