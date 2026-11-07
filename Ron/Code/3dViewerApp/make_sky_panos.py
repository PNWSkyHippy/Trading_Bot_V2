"""Builds cloud-free surround panoramas into pov/ (equirectangular, so Render settings > Sky > image uses them
in both the POV render and the Taichi preview).  Whatever is below the horizon is the 'floor dome': it only
shows where no floor object covers it.

    python make_sky_panos.py            ->  pov/sky_techhall.png   sci-fi hall: techno ceiling, ribbed walls, glowing floor grid
                                            pov/sky_stardome.png   night starfield + nebula all the way round (stars under you too)

Then: Render settings > Sky = image > Choose image..., and delete the cloud layers in the Director (Clouds tab).
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
POV = os.path.join(HERE, "pov")
W, H = 4096, 2048


def directions():
    """Unit vector per pixel, z up; the picture's centre column faces +x, matching sky_load_image / POV map_type 1."""
    az = (np.arange(W) + 0.5) / W * 2 * np.pi
    el = (0.5 - (np.arange(H) + 0.5) / H) * np.pi
    A, E = np.meshgrid(az, el)
    return np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E), A, E


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hash2(ix, iy, salt=0):
    n = (ix * 374761393 + iy * 668265263 + salt * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def grid_layer(u, v, cell, fp, strong_every=4):
    """Panel plane: dark metal tiles, thin seams, glowing cyan seams every `strong_every`, light fixtures in some tiles.
    u, v = plane coordinates in tile units; fp = pixel footprint in tile units (keeps lines anti-aliased)."""
    fu, fv = u - np.floor(u), v - np.floor(v)
    d = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))              # distance to the nearest seam
    w = np.maximum(0.035, fp)
    seam = 1.0 - smooth(w * 0.5, w * 1.5, d)
    iu, iv = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    tone = 0.55 + 0.45 * hash2(iu, iv, 1)
    strong = ((iu % strong_every == 0) | (iv % strong_every == 0)).astype(float)
    base = np.stack([0.035, 0.05, 0.07], -1) * tone[..., None]
    base += np.stack([0.0, 0.0, 0.0], -1)
    # bevel: tile edges a touch lighter than the middle
    base *= (1.0 + 0.7 * (1.0 - smooth(0.0, 0.25, d)))[..., None]
    glow = seam * (0.25 + 0.75 * strong)
    cyan = np.stack([0.10, 0.85, 1.0], -1)
    col = base + glow[..., None] * cyan * 0.9
    # light panels: a lit rectangle inside ~12% of the tiles
    lit = hash2(iu, iv, 7) > 0.88
    inside = smooth(0.18, 0.24, d) * lit
    col += inside[..., None] * np.stack([0.55, 0.75, 1.0], -1) * 0.85
    # far away the pattern would shimmer: fade to its average
    far = smooth(0.35, 1.2, fp)
    avg = np.stack([0.06, 0.12, 0.17], -1)
    return col * (1 - far[..., None]) + avg * far[..., None]


def tech_hall():
    x, y, z, A, E = directions()
    col = np.zeros((H, W, 3))
    az = A / (2 * np.pi)
    dth = 2 * np.pi / W
    for sign in (1, -1):                                       # ceiling above, floor dome below
        m = sign * z > 0.12
        zz = np.where(m, sign * z, 1.0)
        u, v = x / zz * 5.0, y / zz * 5.0
        r2 = (u * u + v * v) / 25.0
        fp = 5.0 * dth * (1 + r2) * 1.4
        layer = grid_layer(u, v, 1.0, fp)
        if sign < 0:                                           # floor: dimmer, magenta-leaning seams, so up and down differ
            layer = layer[..., ::-1] * np.array([1.0, 0.55, 0.9])
            layer *= 0.7
        col = np.where(m[..., None], layer, col)
        fade = smooth(0.12, 0.3, sign * z)                      # blend into the walls near the horizon
        col = np.where(((sign * z > 0.12) & (sign * z < 0.3))[..., None],
                       col * fade[..., None] + 0 * col, col)
    # walls: dark ribs every 15 degrees, a glowing horizon band and a thin red warning stripe
    wall = np.abs(z) <= 0.3
    rib = np.abs(((az * 24) % 1.0) - 0.5)
    ribs = 0.5 + 0.5 * smooth(0.04, 0.16, rib)
    wcol = np.stack([0.045, 0.06, 0.085], -1) * ribs[..., None]
    seam = np.exp(-((((az * 24) % 1.0) - 0.0) ** 2) * 4000) + np.exp(-((((az * 24) % 1.0) - 1.0) ** 2) * 4000)
    wcol += seam[..., None] * np.array([0.05, 0.35, 0.5])
    band = np.exp(-(z - 0.10) ** 2 * 900)
    wcol += band[..., None] * np.array([0.1, 0.7, 1.0]) * 0.9
    stripe = np.exp(-(z + 0.04) ** 2 * 7000)
    wcol += stripe[..., None] * np.array([1.0, 0.18, 0.08]) * 0.7
    low = np.exp(-(z + 0.17) ** 2 * 1500)
    wcol += low[..., None] * np.array([0.7, 0.2, 0.9]) * 0.5
    blend = smooth(0.3, 0.12, np.abs(z))
    col = np.where(wall[..., None], col * (1 - blend[..., None]) + wcol * blend[..., None], col)
    return col


def noise3(x, y, z, freq, salt):
    """Cheap value noise on direction vectors (trilinear on a hashed lattice)."""
    px, py, pz = x * freq, y * freq, z * freq
    ix, iy, iz = np.floor(px).astype(np.int64), np.floor(py).astype(np.int64), np.floor(pz).astype(np.int64)
    fx, fy, fz = px - ix, py - iy, pz - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = hash2(ix + dx + iz * 31 + dz * 31, iy + dy + (iz + dz) * 17, salt)
                out = out + h * (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
    return out


def star_dome(seed=11):
    x, y, z, A, E = directions()
    rng = np.random.default_rng(seed)
    # nebula: two tinted fbm clouds, kept dim and patchy so it reads as depth, not fog
    n = 0
    amp = 0.5
    for o in range(5):
        n = n + amp * noise3(x, y, z, 1.6 * 2 ** o, 3 + o)
        amp *= 0.5
    n2 = noise3(x + 3.1, y - 1.7, z + 0.4, 2.3, 21)
    neb1 = smooth(0.42, 0.85, n) * smooth(0.25, 0.8, n2)
    neb2 = smooth(0.5, 0.9, noise3(x - 2.0, y + 5.0, z, 1.1, 33) * 0.6 + 0.4 * n2)
    col = np.stack([0.006, 0.008, 0.022], -1) * np.ones((H, W, 1))
    col += neb1[..., None] * np.array([0.30, 0.08, 0.38]) * 0.7
    col += neb2[..., None] * np.array([0.04, 0.16, 0.34]) * 0.6
    # a faint Milky-Way band across a tilted great circle
    nx, ny, nz = 0.35, -0.2, 0.91
    nlen = (nx * nx + ny * ny + nz * nz) ** 0.5
    dist = (x * nx + y * ny + z * nz) / nlen
    band = np.exp(-dist ** 2 * 18) * (0.4 + 0.6 * n)
    col += band[..., None] * np.array([0.30, 0.28, 0.40]) * 0.5
    # stars: random directions splatted with a gaussian, widened by 1/cos(el) so poles aren't pinched
    N = 14000
    sz = rng.uniform(-1, 1, N)
    saz = rng.uniform(0, 2 * np.pi, N)
    mag = rng.power(6.0, N)                                    # mostly dim, a few bright
    tint = rng.uniform(0, 1, N)
    px = (saz / (2 * np.pi) * W).astype(int) % W
    py = ((0.5 - np.arcsin(sz) / np.pi) * H).astype(int).clip(0, H - 1)
    stars = np.zeros((H, W, 3))
    base = np.stack([1.0 - 0.3 * tint, 0.9 - 0.1 * tint, 0.8 + 0.2 * tint], 1) * (0.15 + 1.6 * mag[:, None] ** 2)
    np.add.at(stars, (py, px), base)
    # blur: separable gaussian, wider in x toward the poles is skipped (stars are tiny); two passes give a soft core + halo
    def blur(a, s):
        k = np.exp(-(np.arange(-3 * s, 3 * s + 1) ** 2) / (2.0 * s * s))
        k /= k.sum()
        a = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, a) if False else a
        out = np.zeros_like(a)
        for i, w in enumerate(k):
            out += w * np.roll(a, i - 3 * s, axis=1)
        o2 = np.zeros_like(out)
        for i, w in enumerate(k):
            o2 += w * np.roll(out, i - 3 * s, axis=0)
        return o2
    col += blur(stars, 1) * 9.0 + blur(stars, 2) * 6.0
    # a few big soft glows (distant suns), one warm, one cool
    for gx, gy, gz, c, s in ((0.7, 0.5, 0.25, (1.0, 0.65, 0.35), 260.0), (-0.4, -0.8, 0.3, (0.5, 0.7, 1.0), 380.0),
                             (0.1, -0.3, -0.9, (1.0, 0.85, 0.7), 300.0)):
        ln = (gx * gx + gy * gy + gz * gz) ** 0.5
        d2 = 1.0 - (x * gx + y * gy + z * gz) / ln
        col += (np.exp(-d2 * s) * 0.9 + np.exp(-d2 * s * 14) * 1.5)[..., None] * np.array(c)
    return col


def save(col, name):
    img = (np.clip(col, 0, 1) ** (1 / 1.0) * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img).save(os.path.join(POV, name), optimize=True)
    print("wrote", os.path.join(POV, name), img.shape)


if __name__ == "__main__":
    os.makedirs(POV, exist_ok=True)
    which = sys.argv[1:] or ["tech", "stars"]
    if "tech" in which:
        save(tech_hall(), "sky_techhall.png")
    if "stars" in which:
        save(star_dome(), "sky_stardome.png")
