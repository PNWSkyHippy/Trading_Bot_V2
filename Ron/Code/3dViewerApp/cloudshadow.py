"""Cloud-layer ground shadows for the Taichi preview (an approximation of what POV-Ray renders).

Pure numpy, no Tk/Taichi.  Each cloud layer is a flat noise pattern at height `alt` that drifts along its heading;
a ground point is shadowed where the ray towards the sun crosses a dense bit of a layer.  Z-up, compass headings
(x = east = sin, y = north = cos), same maths as pov_export.cloud_pov (value-noise fbm stands in for POV's bozo).
"""
import math

import numpy as np


def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + int(seed) * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF).astype(np.float64) / 65535.0


def _vnoise(x, y, seed):
    ix, iy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy


def _fbm(x, y, seed, octaves=5):
    tot, amp, norm = np.zeros_like(x), 0.5, 0.0
    for o in range(octaves):
        tot += amp * _vnoise(x * (2.0 ** o), y * (2.0 ** o), seed + o)
        norm += amp
        amp *= 0.5
    n = tot / norm                                    # fbm piles up round 0.5: stretch it so coverage behaves
    return np.clip(0.5 + (n - 0.5) * 2.2, 0.0, 1.0)


def layer_cover(hx, hy, ly, t, index=0):
    """0..1 opacity of one layer {alt, heading, speed, coverage, soft, density, size, seed} at plan point (hx, hy), shot time t."""
    size = max(0.01, float(ly.get("size", 50.0)))
    cov = min(1.0, max(0.0, float(ly.get("coverage", 0.5))))
    soft = min(0.5, max(0.02, float(ly.get("soft", 0.25))))
    den = min(1.0, max(0.0, float(ly.get("density", 0.7))))
    h = math.radians(float(ly.get("heading", 270.0)))
    sp = float(ly.get("speed", 0.0)) * float(t)
    seed = float(ly.get("seed", 0)) + index
    th = 0.08 + (1.0 - cov) * 0.67
    tx, ty = math.sin(h) * sp + seed * 37.1, math.cos(h) * sp + seed * 91.7
    n = _fbm((hx - tx) / size, (hy - ty) / size, int(seed) * 7 + 3)
    k = np.clip((n - th) / max(soft, 1e-6), 0.0, 1.0)
    return k * k * (3 - 2 * k) * den


def ground_shadow(X, Y, ground_z, clouds, t):
    """Fraction of sunlight blocked (0 = lit, 1 = dark) at ground points X, Y (same-shape arrays) at height ground_z."""
    sun = clouds.get("sun", {})
    az, el = math.radians(float(sun.get("az", 135.0))), math.radians(float(sun.get("el", 55.0)))
    el = max(el, math.radians(3.0))
    sx, sy, sz = math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)
    lit = np.ones_like(X, dtype=np.float64)
    for i, ly in enumerate(clouds.get("layers", [])):
        rise = float(ly.get("alt", 100.0)) - ground_z
        if rise <= 0:
            continue
        k = rise / sz                                 # distance along the sun ray up to the layer
        lit *= 1.0 - layer_cover(X + sx * k, Y + sy * k, ly, t, i)
    return 1.0 - lit
