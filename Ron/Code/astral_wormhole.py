"""
===============================================================================
ASTRAL WORMHOLE: 6-DOF HYPERSPACE & VOLUMETRIC NEBULA TUNNEL ENGINE
===============================================================================
Mac Trackpad & PC Optimized:
  - Natural Trackpad Steering (Up looks UP, Down looks DOWN)
  - Magnetic Tunnel Spine Tether (You NEVER lose the tunnel / get lost in the void!)
  - Effortless Trackpad Flight: Move finger to steer, hold [SHIFT] for WARP SPEED!
  - 100% Silent on macOS (No alert clicks/beeps)
  - 3D Binaural Hyperspace Acoustics (Curvature resonance & wall ionization)
===============================================================================
"""

import math
import random
import time
import threading
import numpy as np

import taichi as ti

# Initialize GPU acceleration (Metal on Apple Silicon, CUDA/Vulkan on PC, or CPU)
try:
    ti.init(arch=ti.gpu)
except Exception:
    ti.init(arch=ti.cpu)

# ---------------------------------------------------------------------------
# Display Field & Resolution
# ---------------------------------------------------------------------------
res_x, res_y = 800, 600
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(res_x, res_y))

# ---------------------------------------------------------------------------
# GPU Volumetric Ray Marching Shader Functions
# ---------------------------------------------------------------------------
@ti.func
def get_path(z: ti.f32, t: ti.f32) -> ti.types.vector(2, ti.f32):
    """Calculates the 3D serpentine curve of the wormhole spine at depth z."""
    x = ti.sin(z * 0.12 + t * 0.35) * 3.2 + ti.sin(z * 0.04) * 1.5
    y = ti.cos(z * 0.10 + t * 0.25) * 2.4 + ti.cos(z * 0.06) * 1.0
    return ti.Vector([x, y])

@ti.func
def fractal_noise_3d(p: ti.types.vector(3, ti.f32), t: ti.f32) -> ti.f32:
    """Multi-octave trigonometric noise for plasma filaments and nebula clouds."""
    q = p + ti.Vector([0.0, 0.0, t * 2.5])
    n1 = ti.sin(q.x * 2.0) * ti.cos(q.y * 2.0) * ti.sin(q.z * 1.5)
    n2 = ti.sin(q.x * 4.2 + q.z * 2.1) * ti.cos(q.y * 3.8 - q.x * 1.5) * 0.5
    n3 = ti.sin(q.x * 8.5 - q.y * 5.2 + q.z * 6.1) * 0.25
    return n1 + n2 + n3

@ti.kernel
def render_wormhole(
    c_pos: ti.types.vector(3, ti.f32),
    c_forward: ti.types.vector(3, ti.f32),
    c_right: ti.types.vector(3, ti.f32),
    c_up: ti.types.vector(3, ti.f32),
    t_clock: ti.f32,
    warp_boost: ti.f32
):
    for x, y in pixels:
        nx = (2.0 * x - res_x) / res_y
        ny = (2.0 * y - res_y) / res_y

        ray_orig = c_pos
        ray_dir = (c_forward + (nx * c_right) + (ny * c_up)).normalized()

        # Volumetric Accumulation Variables
        acc_color = ti.Vector([0.0, 0.0, 0.0])
        transmittance = 1.0

        # Ray Marching Steps
        num_steps = 64
        step_size = 0.35
        cur_dist = 0.4

        for step in range(num_steps):
            if transmittance < 0.02:
                break

            p = ray_orig + cur_dist * ray_dir

            # Wormhole Center Offset
            path_xy = get_path(p.z, t_clock)
            rel_p = p - ti.Vector([path_xy.x, path_xy.y, p.z])

            # Distance from tunnel spine
            rad_dist = ti.sqrt(rel_p.x * rel_p.x + rel_p.y * rel_p.y)
            angle = ti.atan2(rel_p.y, rel_p.x)

            # Rhythmic tunnel radius with breathing dilation waves
            tunnel_radius = 3.6 + 0.6 * ti.sin(p.z * 0.25 - t_clock * 3.0) + 0.3 * ti.cos(angle * 4.0 + p.z * 0.5)

            # Tunnel Wall Density
            wall_dist = rad_dist - tunnel_radius
            plasma_noise = fractal_noise_3d(rel_p * 0.75, t_clock)

            # Inside the tunnel vs near the glowing energy boundary
            density = 0.0
            if wall_dist > -1.4:
                # Gas / energy density increases toward the walls
                norm_d = (wall_dist + 1.4) / 1.4
                density = (norm_d * norm_d * 0.65 + plasma_noise * 0.3)
                density = ti.max(0.0, density)

            # Floating cosmic dust particles inside the tunnel core
            core_dust = ti.max(0.0, ti.sin(p.x * 10.0) * ti.cos(p.y * 10.0) * ti.sin(p.z * 4.0 + t_clock * 8.0) - 0.75) * 2.2
            density += core_dust

            if density > 0.001:
                # Bioluminescent Palette: Cyan core -> Electric Violet/Magenta -> Golden corona
                hue_shift = p.z * 0.08 + t_clock * 0.5 + angle * 0.3
                col_r = 0.5 + 0.5 * ti.sin(hue_shift + 0.0)
                col_g = 0.5 + 0.5 * ti.sin(hue_shift + 2.094)
                col_b = 0.5 + 0.5 * ti.sin(hue_shift + 4.188)

                # Electric edge highlights & warp boost intensity
                glow_int = 1.0 + warp_boost * 1.6 + core_dust * 2.0
                step_color = ti.Vector([col_r, col_g, col_b]) * density * glow_int

                # Beer-Lambert light absorption
                step_transmittance = ti.exp(-density * step_size * 2.4)
                acc_color += step_color * (1.0 - step_transmittance) * transmittance
                transmittance *= step_transmittance

            cur_dist += step_size

        # Deep Space Void & Distant Dimensional Horizon
        if transmittance > 0.0:
            distant_glow = ti.Vector([0.18, 0.08, 0.35]) * (1.0 + ti.sin(t_clock * 2.0) * 0.3)
            acc_color += distant_glow * transmittance

        # Chromatic Warp Flare on Speed Boost
        if warp_boost > 0.1:
            streak = ti.exp(-ti.abs(nx * ny) * 7.0) * warp_boost * 0.35
            acc_color += ti.Vector([0.4, 0.75, 1.0]) * streak

        pixels[x, y] = acc_color


# ---------------------------------------------------------------------------
# Real-Time Hyperspace 3D Spatial Audio Synthesizer
# ---------------------------------------------------------------------------
class HyperspaceAudioEngine:
    def __init__(self):
        self.sample_rate = 44100
        self.has_audio = False
        self.running = True
        self.speed = 1.0
        self.wall_dist = 2.0
        self.bank_angle = 0.0

        try:
            import pygame
            pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=1024)
            pygame.mixer.set_num_channels(8)
            self.has_audio = True

            # Channel 0: Ambient Hyperspace Drone
            self.drone_ch = pygame.mixer.Channel(0)

            # Generate seamless 3.5s looping Hyperspace Drone
            dur = 3.5
            n = int(self.sample_rate * dur)
            t = np.linspace(0.0, dur, n, endpoint=False, dtype=np.float32)

            # Ethereal Hyperspace Chord (65Hz Sub, 130Hz Octave, 195Hz Fifth, 260Hz Resonance)
            h1 = np.sin(2.0 * np.pi * 65.0 * t) * 0.4
            h2 = np.sin(2.0 * np.pi * 130.0 * t) * 0.3
            h3 = np.sin(2.0 * np.pi * 195.0 * t) * 0.2
            h4 = np.sin(2.0 * np.pi * 260.0 * t + np.sin(2.0 * np.pi * 0.5 * t) * 2.0) * 0.15
            drone = (h1 + h2 + h3 + h4) * 0.45

            stereo = np.column_stack((drone * 32767, drone * 32767)).astype(np.int16)
            self.drone_snd = pygame.sndarray.make_sound(stereo)
            self.drone_ch.play(self.drone_snd, loops=-1)
            self.drone_ch.set_volume(0.35, 0.35)

            # Background Crackle Thread for wall ionization
            self.crackle_thread = threading.Thread(target=self._crackle_loop, daemon=True)
            self.crackle_thread.start()

            print("🔊 3D Hyperspace Audio: [Binaural Resonance Engine] Active & Streaming!")
        except Exception as e:
            print(f"⚠️ Hyperspace Audio note: {e}")

    def update_flight(self, speed_factor, wall_proximity, bank):
        self.speed = float(speed_factor)
        self.wall_dist = float(wall_proximity)
        self.bank_angle = float(bank)

        if self.has_audio and self.drone_ch:
            vol = float(np.clip(0.3 + (self.speed - 1.0) * 0.35, 0.15, 0.9))
            pan = float(np.clip(self.bank_angle * 0.6, -1.0, 1.0))
            vol_l = vol * float(np.sqrt(max(0.0, (1.0 - pan) * 0.5)))
            vol_r = vol * float(np.sqrt(max(0.0, (1.0 + pan) * 0.5)))
            self.drone_ch.set_volume(vol_l, vol_r)

    def _crackle_loop(self):
        """Generates soft plasma ionization crackles when skimming close to the wormhole walls."""
        import pygame
        while self.running:
            if self.wall_dist < 1.2 and self.has_audio:
                dur = 0.12
                n = int(self.sample_rate * dur)
                noise = np.random.uniform(-0.15, 0.15, n).astype(np.float32)
                vol = (1.2 - self.wall_dist) * 0.4
                pan = float(np.clip(self.bank_angle, -1.0, 1.0))
                l = (noise * vol * np.sqrt(max(0.0, (1.0 - pan) * 0.5)) * 32767).astype(np.int16)
                r = (noise * vol * np.sqrt(max(0.0, (1.0 + pan) * 0.5)) * 32767).astype(np.int16)
                snd = pygame.sndarray.make_sound(np.column_stack((l, r)))
                ch = pygame.mixer.Channel(2)
                if ch:
                    ch.play(snd)
            time.sleep(random.uniform(0.08, 0.25))

    def stop(self):
        self.running = False
        if self.has_audio:
            try:
                import pygame
                pygame.mixer.stop()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Main Astral Flight Engine (Trackpad Optimized + Auto-Spine Guide)
# ---------------------------------------------------------------------------
def main():
    audio = HyperspaceAudioEngine()

    # Camera State in Spacetime
    cam_pos = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    cam_yaw = 0.0
    cam_pitch = 0.0
    user_offset_x = 0.0
    user_offset_y = 0.0

    base_speed = 9.0

    gui = ti.GUI("Astral Wormhole: Hyperspace & Nebula Tunnel", res=(res_x, res_y))

    time_clock = 0.0
    last_frame_time = time.time()
    fps = 60.0

    print("\n" + "=" * 70)
    print("🌀 ASTRAL TRACKPAD CONTROLS (Natural & Smooth):")
    print("  [Move Trackpad]       : Steer Aim Naturally (Up = UP, Down = DOWN)")
    print("  [SHIFT (Hold)]        : Engage WARP SPEED BOOST (2.5x Speed!)")
    print("  [Click Trackpad]      : Reverse / Brake")
    print("  [Auto-Spine Tether]   : ACTIVE (Keeps you riding the hyperspace tube!)")
    print("  [ESC]                 : Exit")
    print("=" * 70 + "\n")

    while gui.running:
        now = time.time()
        dt = max(0.001, min(now - last_frame_time, 0.1))
        last_frame_time = now
        fps = 0.9 * fps + 0.1 * (1.0 / dt)
        time_clock += dt

        # -------------------------------------------------------------
        # 1. Event Handling
        # -------------------------------------------------------------
        for e in gui.get_events(ti.GUI.PRESS):
            if e.key == ti.GUI.ESCAPE:
                gui.running = False

        # -------------------------------------------------------------
        # 2. Natural Trackpad Cursor Steering (Up = UP, Down = DOWN)
        # -------------------------------------------------------------
        cursor_x, cursor_y = gui.get_cursor_pos()
        # Normalized offset from screen center (-1.0 to 1.0)
        target_yaw = (cursor_x - 0.5) * 2.2
        target_pitch = (cursor_y - 0.5) * 1.8  # Inverted so moving finger UP looks UP!

        # Smooth interpolation to target angle
        cam_yaw += (target_yaw - cam_yaw) * 0.15
        cam_pitch += (target_pitch - cam_pitch) * 0.15

        # -------------------------------------------------------------
        # 3. Dynamic Serpentine Wormhole Spine Tracking
        # -------------------------------------------------------------
        # Calculate where the tunnel center is at our current Z depth
        spine_x = math.sin(cam_pos[2] * 0.12 + time_clock * 0.35) * 3.2 + math.sin(cam_pos[2] * 0.04) * 1.5
        spine_y = math.cos(cam_pos[2] * 0.10 + time_clock * 0.25) * 2.4 + math.cos(cam_pos[2] * 0.06) * 1.0

        # User steering offsets within the tunnel cylinder
        user_offset_x += (target_yaw * 1.4 - user_offset_x) * 0.08
        user_offset_y += (target_pitch * 1.2 - user_offset_y) * 0.08

        # Smooth Magnetic Tether: Keeps camera riding inside the tunnel forever!
        cam_pos[0] = spine_x + user_offset_x
        cam_pos[1] = spine_y + user_offset_y

        # Forward Flight Velocity
        is_warp = gui.is_pressed(ti.GUI.SHIFT)
        is_brake = gui.is_pressed(ti.GUI.LMB, ti.GUI.RMB, ti.GUI.DOWN, 's', 'S')
        speed_multiplier = 2.6 if is_warp else (0.4 if is_brake else 1.0)

        # Advance forward through the spacetime tube
        cam_pos[2] += base_speed * speed_multiplier * dt

        # -------------------------------------------------------------
        # 4. Camera Orientation Vectors
        # -------------------------------------------------------------
        forward = np.array([
            math.sin(cam_yaw) * math.cos(cam_pitch),
            math.sin(cam_pitch),
            math.cos(cam_yaw) * math.cos(cam_pitch)
        ], dtype=np.float32)
        forward = forward / np.linalg.norm(forward)

        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        right = np.cross(forward, world_up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        # -------------------------------------------------------------
        # 5. Audio Engine Sync
        # -------------------------------------------------------------
        wall_proximity = max(0.0, 3.6 - math.sqrt(user_offset_x ** 2 + user_offset_y ** 2))
        audio.update_flight(
            speed_factor=speed_multiplier,
            wall_proximity=wall_proximity,
            bank=user_offset_x / 2.5
        )

        # -------------------------------------------------------------
        # 6. GPU Volumetric Ray Marching Pass
        # -------------------------------------------------------------
        c_pos_vec = ti.Vector([cam_pos[0], cam_pos[1], cam_pos[2]])
        c_forward_vec = ti.Vector([forward[0], forward[1], forward[2]])
        c_right_vec = ti.Vector([right[0], right[1], right[2]])
        c_up_vec = ti.Vector([up[0], up[1], up[2]])
        warp_val = 1.0 if is_warp else 0.0

        render_wormhole(
            c_pos_vec,
            c_forward_vec,
            c_right_vec,
            c_up_vec,
            time_clock,
            warp_val
        )

        # -------------------------------------------------------------
        # 7. Render HUD & Blit
        # -------------------------------------------------------------
        gui.set_image(pixels)
        gui.text(content=f"HYPERSPACE ENGINE: {fps:.1f} FPS", pos=(0.04, 0.95), color=0x00FFDD, font_size=18)
        gui.text(content="[Move Trackpad] Steer  [SHIFT] Warp Speed  [Click] Brake", pos=(0.04, 0.06), color=0xFFAAFF, font_size=14)
        if is_warp:
            gui.text(content="⚡ WARP SPEED ENGAGED! ⚡", pos=(0.34, 0.92), color=0xFFFF44, font_size=18)

        gui.show()

    audio.stop()


if __name__ == "__main__":
    main()
