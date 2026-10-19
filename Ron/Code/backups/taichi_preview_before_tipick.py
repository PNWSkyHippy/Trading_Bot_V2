"""taichi_preview.py - fast GPU fly-through of the viewer3d scene (Taichi GGUI).

Started by viewer3d's "Taichi preview" button:   python taichi_preview.py <mesh .npz>
The viewer rewrites the .npz whenever the scene is saved; this window reloads it.
Plain colors only - no image textures, CSG cuts or hollows (POV-Ray render has those).

    right-drag   look around          W A S D   move        Q / E   down / up
    Shift        5x faster            R         back to the viewer's camera
    P            play / stop the Camera Director's path (Director: "Play in Taichi" starts it too)
"""
import os
import sys
import time

import numpy as np
import taichi as ti

ti.init(arch=ti.gpu, offline_cache=True)     # Vulkan/CUDA on the PC, Metal on the Mac
ARCH = ti.lang.impl.current_cfg().arch.name
print(f"Taichi preview on {ARCH}")


class Buf:
    """Fixed-size GPU fields that grow (doubling) when the scene gets bigger."""
    def __init__(self):
        self.cap, self.n = 0, 0
        self.fields = None

    def load(self, *arrays):
        n = len(arrays[0])
        if n > self.cap:
            self.cap = max(1024, 1 << (n - 1).bit_length())
            self.fields = [ti.Vector.field(3, ti.f32, self.cap) for _ in arrays]
        for f, a in zip(self.fields or [], arrays):
            pad = np.zeros((self.cap, 3), np.float32)
            pad[:n] = a
            f.from_numpy(pad)
        self.n = n


def load(path):
    for _ in range(5):                       # the viewer may be mid-write
        try:
            with np.load(path) as d:
                return {k: d[k] for k in d.files}
        except (OSError, ValueError, EOFError):
            time.sleep(0.1)
    return None


def main():
    path = sys.argv[1]
    win = ti.ui.Window("viewer3d - Taichi preview", (1280, 800), vsync=True)
    canvas, scene, gui = win.get_canvas(), win.get_scene(), win.get_gui()
    cam = ti.ui.Camera()
    tris, lines = Buf(), Buf()
    data, stamp, cam_id, play_id, radius = None, None, None, None, 1.0
    play_t0 = None                           # time the camera path started playing, or None

    def to_view(d):
        eye, tgt = d["eye"].astype(float), d["target"].astype(float)
        cam.position(*eye)
        cam.lookat(*tgt)
        cam.up(0.0, 0.0, 1.0)                # the viewer is Z-up
        cam.fov(float(d["fov"]))

    def n_path():
        return len(data["path_cam"]) if data is not None and "path_cam" in data else 0

    def path_frame(i):
        cam.position(*data["path_cam"][i].astype(float))
        cam.lookat(*data["path_look"][i].astype(float))
        cam.up(*data["path_up"][i].astype(float))
        cam.fov(float(data["path_fov"][i]))

    frame = 0
    while win.running:
        if frame % 15 == 0:                  # ~4 times a second: has the viewer saved?
            try:
                t = os.path.getmtime(path)
            except OSError:
                t = stamp
            if t != stamp:
                d = load(path)
                if d is not None:
                    stamp, data = t, d
                    tris.load(d["verts"], d["normals"], d["colors"])
                    lines.load(d["lverts"], d["lcolors"])
                    radius = float(d["radius"])
                    cam.z_near(radius * 1e-4)
                    cam.z_far(radius * 20)
                    if int(d["cam_id"]) != cam_id:     # viewer asked to jump to its view
                        cam_id = int(d["cam_id"])
                        to_view(d)
                    pid = int(d.get("play_id", 0))
                    if (play_id is None and bool(d.get("start_play", False))) or \
                            (play_id is not None and pid != play_id):
                        play_t0 = time.time() if n_path() else None   # director: "Play in Taichi"
                    play_id = pid
        frame += 1

        for e in win.get_events(ti.ui.PRESS):
            if e.key == "p" and n_path():                 # (re)play the camera path
                play_t0 = None if play_t0 is not None else time.time()
                if play_t0 is None:
                    cam.up(0.0, 0.0, 1.0)
            elif e.key == "r" and data is not None:
                play_t0 = None
                to_view(data)
        if play_t0 is not None:
            i = int((time.time() - play_t0) * float(data["path_fps"]))
            if i >= n_path():
                play_t0 = None
                i = n_path() - 1
            path_frame(i)
            if play_t0 is None:
                cam.up(0.0, 0.0, 1.0)                     # done: free flying again from the last frame
        else:
            fast = 5.0 if win.is_pressed(ti.ui.SHIFT) else 1.0
            cam.track_user_inputs(win, movement_speed=radius * 0.004 * fast, hold_key=ti.ui.RMB)

        scene.set_camera(cam)
        scene.ambient_light((0.35, 0.35, 0.35))
        pos = cam.curr_position
        scene.point_light(pos=(float(pos[0]), float(pos[1]), float(pos[2])), color=(0.75, 0.75, 0.75))
        sun = (data["center"] + np.array([0.6, -0.4, 1.0]) * radius * 4) if data is not None else (0, 0, 1)
        scene.point_light(pos=tuple(float(v) for v in sun), color=(0.45, 0.45, 0.45))
        if tris.n:
            v, nrm, col = tris.fields
            scene.mesh(v, normals=nrm, per_vertex_color=col, two_sided=True, vertex_count=tris.n)
        if lines.n:
            lv, lc = lines.fields
            scene.lines(lv, width=2, per_vertex_color=lc, vertex_count=lines.n)
        canvas.set_background_color((0.11, 0.12, 0.14))
        canvas.scene(scene)
        with gui.sub_window("preview", 0.01, 0.01, 0.42, 0.13) as g:
            g.text(f"{tris.n // 3:,} triangles   GPU: {ARCH}")
            g.text("right-drag look | WASD move | Q/E down/up | Shift fast | R reset")
            if play_t0 is not None:
                i = min(int((time.time() - play_t0) * float(data["path_fps"])), n_path() - 1)
                g.text(f"camera path: frame {i + 1} / {n_path()}   (P stop)")
            elif n_path():
                g.text(f"camera path: {n_path()} frames (orange)   P play")
        win.show()


if __name__ == "__main__":
    main()
