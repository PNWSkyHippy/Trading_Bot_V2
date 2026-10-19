"""taichi_preview.py - fast GPU fly-through of the viewer3d scene (Taichi GGUI).

Started by viewer3d's "Taichi preview" button:   python taichi_preview.py <mesh .npz>
The viewer rewrites the .npz whenever the scene is saved; this window reloads it.
Plain colors only - no image textures, CSG cuts or hollows (POV-Ray render has those).

    right-drag   look around          W A S D   move        Q / E   down / up
    Shift        5x faster            R         back to the viewer's camera
    left-click   select it in the viewer's tree (Shift adds); selected objects show lighter
    left-drag    move it (and its group) across the floor; hold Ctrl for up / down.
                 On release the viewer does it as a Move (saved + listed in its transforms, like Move by)
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


def ray_tris(o, d, V):
    """Distance along the ray o + t*d to each triangle of V (T, 3, 3); inf where it misses."""
    e1, e2 = V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    inv = 1.0 / np.where(ok, det, 1.0)
    s = o - V[:, 0]
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = (q @ d) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    return np.where(ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0), t, np.inf)


def ray_segs(o, d, A, B, tol):
    """Distance along the ray to each segment A-B that passes within tol*distance of it
    (tol = an angle, so a few pixels wide at any depth); inf otherwise."""
    e = B - A
    w = o - A
    b, c = e @ d, np.einsum("ij,ij->i", e, e)
    dd, ee = w @ d, np.einsum("ij,ij->i", e, w)
    den = c - b * b
    t = np.clip(np.where(den > 1e-12, (ee - b * dd) / np.where(den > 1e-12, den, 1), 0), 0, 1)
    s = np.maximum(b * t - dd, 0)
    gap = np.linalg.norm(o + s[:, None] * d - (A + t[:, None] * e), axis=1)
    return np.where((s > 0) & (gap <= tol * s), s, np.inf)


def pick(data, o, d, tol):
    """(object number, distance) of what the ray hits first - planes only when nothing else
    is there - or (-1, inf)."""
    own_t, own_l, plane = data["tri_obj"], data["seg_obj"], data["obj_plane"]
    best, who = np.inf, -1
    if len(own_t):
        t = ray_tris(o, d, data["verts"].reshape(-1, 3, 3).astype(float))
        t[own_t < 0] = np.inf
        i = int(np.argmin(t))
        best, who = t[i], own_t[i]
    plane_hit = None
    if len(own_l):
        L = data["lverts"].reshape(-1, 2, 3).astype(float)
        s = ray_segs(o, d, L[:, 0], L[:, 1], tol)
        s[own_l < 0] = np.inf
        is_plane = plane[np.maximum(own_l, 0)] & (own_l >= 0)
        sp = np.where(is_plane, s, np.inf)
        s[is_plane] = np.inf
        i = int(np.argmin(s))
        if s[i] < best:
            best, who = s[i], own_l[i]
        j = int(np.argmin(sp))
        if np.isfinite(sp[j]):
            plane_hit = own_l[j], sp[j]
    Q = data.get("plane_quads")
    if plane_hit is None and Q is not None and len(Q):         # inside a plane's grid
        T = np.concatenate([Q[:, [0, 1, 2]], Q[:, [0, 2, 3]]])
        t = ray_tris(o, d, T)
        i = int(np.argmin(t))
        if np.isfinite(t[i]):
            plane_hit = np.concatenate([data["plane_obj"]] * 2)[i], t[i]
    if not np.isfinite(best):
        return plane_hit if plane_hit is not None else (-1, np.inf)
    return int(who), float(best)


def plane_hit(o, d, p0, n):
    """Where the ray o + t*d meets the plane through p0 with normal n (None if it can't)."""
    den = d @ n
    if abs(den) < 1e-9:
        return None
    t = ((p0 - o) @ n) / den
    return o + t * d if t > 0 else None


def main():
    path = sys.argv[1]
    win = ti.ui.Window("viewer3d - Taichi preview", (1280, 800), vsync=True)
    canvas, scene, gui = win.get_canvas(), win.get_scene(), win.get_gui()
    cam = ti.ui.Camera()
    tris, lines = Buf(), Buf()
    data, stamp, cam_id, play_id, radius = None, None, None, None, 1.0
    play_t0 = None                           # time the camera path started playing, or None
    fov = [45.0]                             # vertical, degrees (the Camera doesn't report it back)
    test = os.environ.get("TI_PICK_TEST")    # self-test: compare picks against the drawn image

    def set_fov(f):
        fov[0] = float(f)
        cam.fov(fov[0])

    def to_view(d):
        eye, tgt = d["eye"].astype(float), d["target"].astype(float)
        cam.position(*eye)
        cam.lookat(*tgt)
        cam.up(0.0, 0.0, 1.0)                # the viewer is Z-up
        set_fov(d["fov"])

    def ray(cx, cy):
        """Eye and unit direction through window point (cx, cy), both 0..1 with y up."""
        eye = np.array([float(v) for v in cam.curr_position])
        f = np.array([float(v) for v in cam.curr_lookat]) - eye
        f /= np.linalg.norm(f)
        r = np.cross(f, [float(v) for v in cam.curr_up])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        w, h = win.get_window_shape()
        t = np.tan(np.radians(fov[0]) / 2)
        d = f + (2 * cx - 1) * t * (w / h) * r + (2 * cy - 1) * t * u
        return eye, d / np.linalg.norm(d), 2 * t / h          # last: radians per pixel

    def n_path():
        return len(data["path_cam"]) if data is not None and "path_cam" in data else 0

    def path_frame(i):
        cam.position(*data["path_cam"][i].astype(float))
        cam.lookat(*data["path_look"][i].astype(float))
        cam.up(*data["path_up"][i].astype(float))
        set_fov(data["path_fov"][i])

    drag = None                              # left-drag in progress: what, where it started, plane
    pending = []                             # (object mask, offset, ticket): moves sent, viewer not done yet
    sent = [None]                            # tickets handed out (starts at the viewer's moves_done)
    shown = [None]                           # offsets now on the GPU (to skip re-uploading)

    def show_offsets():
        """Draw dragged / not-yet-saved objects at their moved spots."""
        n = len(data["obj_iids"])
        off = np.zeros((n + 1, 3))           # last row: owner -1 (grid etc.) never moves
        for mask, dv, _t in pending + ([(drag["mask"], drag["delta"], 0)] if drag else []):
            off[:n][mask] += dv
        key = off.tobytes()
        if key == shown[0]:
            return
        shown[0] = key
        own_v = np.repeat(data["tri_obj"], 3)
        own_l = np.repeat(data["seg_obj"], 2)
        tris.load(data["verts"] + off[own_v].astype(np.float32), data["normals"], data["colors"])
        lines.load(data["lverts"] + off[own_l].astype(np.float32), data["lcolors"])

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
                    shown[0] = None
                    done = int(d.get("moves_done", 0))
                    if sent[0] is None:
                        sent[0] = done
                    pending[:] = [p for p in pending if p[2] > done]   # the viewer has these now
                    if drag and len(drag["mask"]) != len(d["obj_iids"]):
                        drag = None                                    # scene changed under the drag
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
            elif e.key == ti.ui.LMB and data is not None and "tri_obj" in data:
                cx, cy = win.get_cursor_pos()
                if cx < 0.43 and cy > 1 - 0.14:           # on the HUD box
                    continue
                o, d, px = ray(cx, cy)
                k, dist = pick(data, o, d, px * 5)
                iid = str(data["obj_iids"][k]) if k >= 0 else None
                if test:
                    print(f"cursor {cx:.4f} {cy:.4f} -> {iid}")
                if iid:
                    print(f"PICK {iid} {'add' if win.is_pressed(ti.ui.SHIFT) else 'set'}", flush=True)
                    grp = int(data["obj_move"][k]) if "obj_move" in data else -1
                    if grp >= 0:                              # hold and drag to move it
                        drag = {"k": k, "mask": data["obj_move"] == grp, "p0": o + d * dist,
                                "delta": np.zeros(3), "at": (cx, cy), "moved": False}

        if drag is not None:
            cx, cy = win.get_cursor_pos()
            if not win.is_pressed(ti.ui.LMB):                 # let go: tell the viewer
                if drag["moved"]:
                    dv = np.round(drag["delta"], 3)
                    sent[0] = (sent[0] or 0) + 1
                    pending.append((drag["mask"], dv, sent[0]))
                    print(f"MOVE {data['obj_iids'][drag['k']]} {dv[0]:g} {dv[1]:g} {dv[2]:g}", flush=True)
                drag = None
            else:
                w, h = win.get_window_shape()
                if abs(cx - drag["at"][0]) * w + abs(cy - drag["at"][1]) * h > 4:
                    drag["moved"] = True
                if drag["moved"]:
                    o, d, _px = ray(cx, cy)
                    if win.is_pressed(ti.ui.CTRL):            # Ctrl: up / down, on a wall facing you
                        n = np.array([d[0], d[1], 0.0])
                        n = n / np.linalg.norm(n) if np.linalg.norm(n) > 1e-6 else np.array([1.0, 0, 0])
                    else:                                     # flat across the floor
                        n = np.array([0.0, 0.0, 1.0])
                    p0 = drag["p0"] + drag["delta"]           # (switching Ctrl mid-drag keeps going smoothly)
                    hit = plane_hit(o, d, p0, n)
                    if hit is not None and np.linalg.norm(hit - p0) < radius * 4:
                        step = hit - p0
                        if not win.is_pressed(ti.ui.CTRL):
                            step[2] = 0.0
                        else:
                            step[:2] = 0.0
                        drag["delta"] = drag["delta"] + step
        if data is not None and "tri_obj" in data and (pending or drag or shown[0] is not None):
            show_offsets()
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
            if drag and drag["moved"]:
                dv = drag["delta"]
                g.text(f"moving {dv[0]:.3f}, {dv[1]:.3f}, {dv[2]:.3f}   (Ctrl: up / down)")
            else:
                g.text("left-click select (Shift adds) | left-drag move (Ctrl: up/down)")
            if play_t0 is not None:
                i = min(int((time.time() - play_t0) * float(data["path_fps"])), n_path() - 1)
                g.text(f"camera path: frame {i + 1} / {n_path()}   (P stop)")
            elif n_path():
                g.text(f"camera path: {n_path()} frames (orange)   P play")
        if test and data is not None and frame == 90:
            self_test(win, data, ray)
        win.show()


def self_test(win, data, ray):
    """Pick a grid of window points (triangles only) and check hit / no-hit against the pixels:
    tells whether the ray math (fov, aspect, y direction) matches what Taichi draws."""
    img = win.get_image_buffer_as_numpy()               # (w, h, 4)
    w, h = img.shape[:2]
    bg = np.array([0.11, 0.12, 0.14])
    V = data["verts"].reshape(-1, 3, 3).astype(float)
    C = data["colors"][::3].astype(float)

    def chroma(c):
        return c / (c.sum() + 1e-6)
    agree = {"y up": 0, "y down": 0}
    n = 0
    for gx in np.linspace(0.47, 0.97, 24):
        for gy in np.linspace(0.03, 0.83, 16):
            o, d, _ = ray(gx, gy)
            t = ray_tris(o, d, V)
            i = int(np.argmin(t))
            x = min(int(gx * w), w - 1)
            for name, y in (("y up", int(gy * h)), ("y down", int((1 - gy) * h))):
                px = img[x, min(max(y, 0), h - 1), :3].astype(float)
                if not np.isfinite(t[i]):
                    ok = np.abs(px - bg).max() < 0.02 or px.max() - px.min() < 0.03   # background / grey grid
                else:
                    ok = np.abs(chroma(px) - chroma(C[i])).max() < 0.04
                agree[name] += bool(ok)
            n += 1
    print(f"self-test {n} points  agree: " + "  ".join(f"{k} {v}/{n}" for k, v in agree.items()), flush=True)


if __name__ == "__main__":
    main()
