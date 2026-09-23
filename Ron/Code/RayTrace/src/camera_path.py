"""Camera director data and export functions. No Tk or renderer is needed here.

A shot is a plain dictionary: a list of camera moves, a reference object, and
lights. Keeping the data separate makes it easy to read, test, and edit by hand.
"""

import ast
import copy
import json
import math
import os
import pprint
import re
import tempfile
from pathlib import Path


def default_shot():
    return {
        "name": "Camera sweep",
        "segments": [{
            "kind": "Arc", "a": [-8, 4, -12], "b": [0, 6, -15],
            "c": [8, 4, -12], "target_a": [0, 1, 0], "target_c": [0, 1, 0],
            "steps": 48, "fov_a": 45, "fov_c": 45,
        }],
        "object": {"kind": "Sphere", "position": [0, 1, 0], "size": 1, "color": "#75baff"},
        "lights": [{"position": [-4, 8, -6], "color": "#ffffff", "brightness": 1.5}],
        "fps": 24,
        "ground_y": 0,
    }


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(a, value):
    return tuple(x * value for x in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def unit(a):
    length = math.sqrt(dot(a, a))
    if length < 1e-9:
        raise ValueError("Camera position and aim point must be different.")
    return mul(a, 1 / length)


def mix(a, b, t):
    return add(mul(a, 1 - t), mul(b, t))


def camera_basis(position, target, roll=0):
    """Camera axes used by both the wireframe preview and POV export."""
    forward = unit(sub(target, position))
    up_hint = (0, 1, 0) if abs(forward[1]) < 0.999 else (0, 0, 1)
    right = unit(cross(up_hint, forward))
    up = unit(cross(forward, right))
    # Rotate the camera around its viewing direction, without moving its aim.
    angle = math.radians(roll)
    right, up = (add(mul(right, math.cos(angle)), mul(up, math.sin(angle))),
                 add(mul(up, math.cos(angle)), mul(right, -math.sin(angle))))
    return right, up, forward


def segment_pose(segment, t):
    """A straight move uses A/C. An arc passes THROUGH B at its halfway time.

    B is not a Bezier control handle. Calculate that handle from B so that the
    quadratic curve actually visits the location the user put on the grid.
    The curve is a smooth quadratic sweep, not necessarily a circular arc.
    """
    a, c = segment["a"], segment["c"]
    if segment["kind"] == "Arc":
        handle = sub(mul(segment["b"], 2), mul(add(a, c), 0.5))
        camera = add(add(mul(a, (1-t)**2), mul(handle, 2*(1-t)*t)), mul(c, t*t))
    else:
        camera = mix(a, c, t)
    return {
        "camera": camera,
        "lookat": mix(segment["target_a"], segment["target_c"], t),
        "vfov": segment["fov_a"] + (segment["fov_c"]-segment["fov_a"])*t,
    }


def check_vector(value, label):
    if len(value) != 3 or not all(math.isfinite(float(x)) for x in value):
        raise ValueError(f"{label} needs three finite numbers: X, Y, Z.")


def rgb(hex_color):
    if len(hex_color) != 7 or hex_color[0] != "#":
        raise ValueError("Colors use #RRGGBB, for example #ff8800.")
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (1, 3, 5))


def validate_shot(shot):
    if not str(shot["name"]).strip():
        raise ValueError("Give the shot a name before saving.")
    if not shot["segments"]:
        raise ValueError("Add at least one camera move.")
    total = 1
    previous = None
    for segment in shot["segments"]:
        if segment["kind"] not in ("Line", "Arc"):
            raise ValueError("Move type must be Line or Arc.")
        for key in ("a", "b", "c", "target_a", "target_c"):
            check_vector(segment[key], key)
        steps = segment["steps"]
        if isinstance(steps, bool) or int(steps) != steps or not 1 <= steps <= 2000:
            raise ValueError("Each move needs 1–2000 frame steps.")
        total += int(steps)
        if previous is not None and (
            tuple(segment["a"]) != tuple(previous["c"])
            or tuple(segment["target_a"]) != tuple(previous["target_c"])
            or segment["fov_a"] != previous["fov_c"]
        ):
            raise ValueError("Each move must start at the previous move's end pose.")
        for key in ("fov_a", "fov_c"):
            if not 1 <= segment[key] <= 170:
                raise ValueError("Field of view must be between 1 and 170 degrees.")
        previous = segment
    if total > 10000:
        raise ValueError("Keep this shot at 10,000 frames or fewer.")
    obj = shot["object"]
    check_vector(obj["position"], "Object position")
    if obj["kind"] not in ("Sphere", "Box"):
        raise ValueError("Object must be Sphere or Box.")
    if not math.isfinite(obj["size"]) or obj["size"] <= 0:
        raise ValueError("Object radius / half-size must be positive.")
    rgb(obj["color"])
    for light in shot["lights"]:
        check_vector(light["position"], "Light position")
        rgb(light["color"])
        if not math.isfinite(light["brightness"]) or light["brightness"] < 0:
            raise ValueError("Light brightness must be zero or greater.")
    if not 1 <= shot["fps"] <= 120:
        raise ValueError("Preview FPS must be between 1 and 120.")
    if not math.isfinite(shot.get("ground_y", 0)):
        raise ValueError("Reference ground Y must be a finite number.")
    if not math.isfinite(shot.get("roll", 0)):
        raise ValueError("Camera roll must be a finite number of degrees.")


def sample_shot(shot):
    """One initial frame plus each move's steps; shared endpoints occur once."""
    validate_shot(shot)
    frames = []
    for index, segment in enumerate(shot["segments"]):
        for step in range(0 if index == 0 else 1, int(segment["steps"])+1):
            pose = segment_pose(segment, step/segment["steps"])
            camera_basis(pose["camera"], pose["lookat"])
            frames.append(pose)
    return frames


def point_text(point):
    return ",".join(f"{x:.9g}" for x in point)


def renderer_frames(shot):
    """Use the same per-frame dictionary interface as the existing renderer."""
    lights = shot["lights"]
    # Book renderer supports two white lights with power 0..1. POV export keeps
    # every light, its color, and its full brightness instead.
    white = [point_text(light["position"]) + f",{min(1, light['brightness']):.6g}" for light in lights[:2]]
    white += ["0,0,0,0"] * (2-len(white))
    return [{
        "camera": point_text(pose["camera"]), "lookat": point_text(pose["lookat"]),
        "vfov": f"{pose['vfov']:.9g}", "light1": white[0], "light2": white[1],
        "filename": f"scene_data/director_{i:04d}.ppm",
    } for i, pose in enumerate(sample_shot(shot), 1)]


def pov_scene_text(shot, pose=None, include_object=True):
    """Export a complete POV scene with exactly the preview object's coordinates."""
    validate_shot(shot)
    pose = pose or segment_pose(shot["segments"][0], 0)
    def vec(value):
        if isinstance(value, str):
            value = [float(x) for x in value.split(",")]
        return "<" + point_text(value) + ">"
    position = pose["camera"]
    target = pose["lookat"]
    position = [float(x) for x in position.split(",")] if isinstance(position, str) else position
    target = [float(x) for x in target.split(",")] if isinstance(target, str) else target
    _, sky, _ = camera_basis(position, target, shot.get("roll", 0))
    lines = [
        "// Generated by RayTrace Camera Director. Units: X right, Y up, Z depth.",
        "#version 3.7;", "global_settings { assumed_gamma 1.0 }",
        "background { color rgb <0.035,0.045,0.07> }",
        "camera {", f"  location {vec(position)}",
        "  right x*image_width/image_height", f"  sky {vec(sky)}",
        # POV angle is horizontal; our editor uses vertical FOV.
        f"  angle degrees(2*atan(tan(radians({float(pose['vfov'])}/2))*image_width/image_height))",
        f"  look_at {vec(target)}", "}",
    ]
    for light in shot["lights"]:
        lines.append(f"light_source {{ {vec(light['position'])} color rgb {vec(mul(rgb(light['color']), light['brightness']))} }}")
    obj = shot["object"]
    center, size = obj["position"], obj["size"]
    shape = f"sphere {{ {vec(center)}, {size:.9g}" if obj["kind"] == "Sphere" else (
        f"box {{ {vec(sub(center, (size,)*3))}, {vec(add(center, (size,)*3))}")
    if include_object:
        lines += [shape, f"  pigment {{ color rgb {vec(rgb(obj['color']))} }}",
                  "  finish { diffuse 0.8 phong 0.25 }", "}"]
    return "\n".join(lines) + "\n"


def camera_span(source):
    """Locate a literal camera, ignoring braces in comments and quoted strings."""
    masked = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
                    lambda match: " " * len(match.group()), source)
    match = re.search(r"\bcamera\s*\{", masked)
    if match is None:
        raise ValueError("The selected POV scene needs a literal camera { ... } block.")
    start = masked.index("{", match.start())
    depth = 0
    end = None
    for i in range(start, len(masked)):
        depth += (masked[i] == "{") - (masked[i] == "}")
        if depth == 0:
            end = i+1
            break
    if end is None:
        raise ValueError("The selected POV scene has an unclosed camera block.")
    return match.start(), end, masked[match.start():end]


def read_pov_camera(source):
    """Read literal coordinates only; do not try to evaluate arbitrary POV code."""
    _, _, camera = camera_span(source)
    result = {}
    for field in ("location", "look_at"):
        match = re.search(r"\b"+field+r"\s*<([^>]+)>", camera)
        if match is None:
            raise ValueError("Import needs literal location <x,y,z> and look_at <x,y,z>. Enter coordinates manually for macro/expression cameras.")
        try:
            value = [float(x.strip()) for x in match.group(1).split(",")]
            check_vector(value, field)
        except ValueError as exc:
            raise ValueError("Camera coordinates contain POV expressions; enter their evaluated XYZ values manually.") from exc
        result[field] = value
    camera_basis(result["location"], result["look_at"])
    return result


def overlay_pov_scene(source, shot, pose, include_object=False):
    """Replace camera with a standard perspective camera; retain original scene.

    Append editor lights (and optionally its object) to the temporary copy.
    """
    start, end, _ = camera_span(source)
    generated = pov_scene_text(shot, pose, include_object)
    camera_start = generated.index("camera {")
    camera_end = generated.index("\n}", camera_start)+2
    return (source[:start] + generated[camera_start:camera_end] + source[end:]
            + "\n// Camera Director additions (original lights retained)\n" + generated[camera_end:])


def pov_animation_text(shot, source=None, include_object=False):
    """A standalone POV animation: frame_number selects an exact sampled pose."""
    poses = sample_shot(shot)
    generated = pov_scene_text(shot, poses[0])
    start = generated.index("camera {")
    end = generated.index("\n}", start)+2
    camera = generated[start:end]
    text = generated if source is None else overlay_pov_scene(source, shot, poses[0], include_object)
    vectors = lambda key: ",\n".join("<"+point_text(pose[key])+">" for pose in poses)
    sky = []
    for pose in poses:
        up = camera_basis(pose["camera"], pose["lookat"], shot.get("roll", 0))[1]
        sky.append("<" + point_text(up) + ">")
    declarations = (
        f"#declare RD_Camera = array[{len(poses)}] {{ {vectors('camera')} }};\n"
        f"#declare RD_Target = array[{len(poses)}] {{ {vectors('lookat')} }};\n"
        f"#declare RD_Sky = array[{len(poses)}] {{ {','.join(sky)} }};\n"
        f"#declare RD_Fov = array[{len(poses)}] {{ {','.join(str(p['vfov']) for p in poses)} }};\n"
        f"#declare RD_Index = min({len(poses)-1}, max(0, frame_number-1));\n"
    )
    dynamic = (
        "camera {\n  location RD_Camera[RD_Index]\n"
        "  right x*image_width/image_height\n  sky RD_Sky[RD_Index]\n"
        "  angle degrees(2*atan(tan(radians(RD_Fov[RD_Index]/2))*image_width/image_height))\n"
        "  look_at RD_Target[RD_Index]\n}\n"
    )
    return text.replace(camera, declarations+dynamic, 1)


# A marked, literal-only section allows saving presets without executing code
# from an imported project or rewriting the hand-edited scenes already present.
BEGIN = "# BEGIN CAMERA DIRECTOR SHOTS"
END = "# END CAMERA DIRECTOR SHOTS"


def load_presets(path):
    text = Path(path).read_text(encoding="utf-8")
    if BEGIN not in text:
        return {}
    block = text.split(BEGIN, 1)[1].split(END, 1)[0]
    tree = ast.parse(block)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign):
        raise ValueError("The Camera Director section should contain only its preset dictionary.")
    presets = ast.literal_eval(tree.body[0].value)
    if not isinstance(presets, dict):
        raise ValueError("Camera Director presets must be a dictionary.")
    return presets


def save_preset(path, shot):
    """Replace only our marked section. Preserve existing scenes and a backup."""
    sample_shot(shot)
    path = Path(path)
    original = path.read_bytes()
    text = original.decode("utf-8")
    presets = load_presets(path)
    presets[shot["name"]] = copy.deepcopy(shot)
    section = BEGIN + "\n# Saved camera moves, objects, and lights. Safe to edit as plain Python data.\n"
    section += "camera_director_shots = " + pprint.pformat(presets, sort_dicts=False, width=95) + "\n" + END
    if BEGIN in text:
        before, tail = text.split(BEGIN, 1)
        _, after = tail.split(END, 1)
        updated = before + section + after
    else:
        updated = text + "\n\n" + section + "\n"
    # Check syntax before touching the include file.
    compile(updated, str(path), "exec")
    backup = path.with_suffix(path.suffix + ".director.bak")
    backup.write_bytes(original)
    fd, temp_name = tempfile.mkstemp(prefix=".director-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(updated)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def save_project(path, shot):
    sample_shot(shot)
    Path(path).write_text(json.dumps(shot, indent=2) + "\n", encoding="utf-8")


def load_project(path):
    shot = json.loads(Path(path).read_text(encoding="utf-8"))
    sample_shot(shot)
    return shot
