"""Run with venv312: python -m pytest Ron/Code/RayTrace/src/test_camera_path.py.

Math/export tests run without Tk. One widget test checks actual editor actions;
it withdraws its windows and never starts an expensive render.
"""

import copy
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_path as cp


def test_roll_changes_up_without_changing_aim_and_reaches_both_pov_exports():
    shot = cp.default_shot()
    shot["roll"] = 90
    pose = cp.sample_shot(shot)[0]
    right, up, forward = cp.camera_basis(pose["camera"], pose["lookat"])
    rolled_right, rolled_up, rolled_forward = cp.camera_basis(pose["camera"], pose["lookat"], 90)
    assert rolled_right == pytest.approx(up)
    assert rolled_up == pytest.approx(cp.mul(right, -1))
    assert rolled_forward == pytest.approx(forward)
    sky = "<" + cp.point_text(rolled_up) + ">"
    assert "sky " + sky in cp.pov_scene_text(shot, pose)
    assert "{ " + sky in cp.pov_animation_text(shot)
    shot["roll"] = float("nan")
    with pytest.raises(ValueError, match="roll"):
        cp.validate_shot(shot)


def test_arc_visits_a_b_c_and_line_does_not_use_arc_handle():
    shot = cp.default_shot()
    move = shot["segments"][0]
    frames = cp.sample_shot(shot)
    assert len(frames) == 49
    assert frames[0]["camera"] == tuple(move["a"])
    assert frames[24]["camera"] == tuple(move["b"])
    assert frames[-1]["camera"] == tuple(move["c"])
    move["kind"] = "Line"
    assert cp.sample_shot(shot)[24]["camera"] == cp.mix(move["a"], move["c"], .5)


def test_connected_segments_have_exact_frame_count_and_independent_data():
    shot = cp.default_shot()
    original = copy.deepcopy(shot)
    move = copy.deepcopy(shot["segments"][0])
    move.update(kind="Line", a=move["c"][:], c=[12, 10, -8], steps=12)
    shot["segments"].append(move)
    frames = cp.sample_shot(shot)
    assert len(frames) == 61
    assert frames[48]["camera"] == tuple(move["a"])
    assert frames[49]["camera"] != tuple(move["a"])
    assert frames[-1]["camera"] == (12, 10, -8)
    assert shot["segments"][0] == original["segments"][0]
    move["a"][0] += 1
    with pytest.raises(ValueError, match="previous"):
        cp.sample_shot(shot)


def test_pan_fov_and_vertical_camera_basis():
    shot = cp.default_shot()
    shot["segments"][0].update(target_c=[2, 3, 0], fov_c=60)
    frame = cp.sample_shot(shot)[24]
    assert frame["lookat"] == (1, 2, 0)
    assert frame["vfov"] == 52.5
    right, up, forward = cp.camera_basis((0, 10, 0), (0, 0, 0))
    assert cp.dot(right, up) == pytest.approx(0)
    assert cp.dot(forward, forward) == pytest.approx(1)


@pytest.mark.parametrize("field,value", [("steps", 0), ("steps", 1.2), ("fov_a", 180), ("a", [0, 1])])
def test_reject_invalid_move(field, value):
    shot = cp.default_shot()
    shot["segments"][0][field] = value
    with pytest.raises(ValueError):
        cp.sample_shot(shot)


def test_presets_preserve_handwritten_include_and_save_backup(tmp_path):
    path = tmp_path / "rayincludes.py"
    original = b"# My handwritten scenes\r\nscene1_keyframes = []\r\n"
    path.write_bytes(original)
    shot = cp.default_shot()
    cp.save_preset(path, shot)
    assert path.read_bytes().startswith(original)
    assert path.with_suffix(".py.director.bak").read_bytes() == original
    assert cp.load_presets(path)[shot["name"]] == shot
    shot["segments"][0]["steps"] = 10
    cp.save_preset(path, shot)
    assert path.read_text().count(cp.BEGIN) == 1
    assert cp.load_presets(path)[shot["name"]]["segments"][0]["steps"] == 10


def test_project_roundtrip_and_renderer_frame_contract(tmp_path):
    shot = cp.default_shot()
    path = tmp_path / "scene.json"
    cp.save_project(path, shot)
    assert cp.load_project(path) == shot
    frame = cp.renderer_frames(shot)[0]
    assert frame["camera"] == "-8,4,-12"
    assert frame["vfov"] == "45"
    assert set(("lookat", "light1", "light2", "filename")).issubset(frame)


def test_pov_keeps_template_geometry_and_injects_colored_light():
    shot = cp.default_shot()
    shot["lights"][0].update(color="#ff8000", brightness=2)
    source = ('// camera { fake }\n#include "colors.inc"\n'
              'camera { location <0,0,-9> look_at <0,0,0> normal { bumps 0.1 } }\n'
              'sphere { <4,2,0>, 3 pigment { color rgb <1,0,0> } }\n')
    result = cp.overlay_pov_scene(source, shot, cp.sample_shot(shot)[0])
    assert '// camera { fake }' in result
    assert '#include "colors.inc"' in result
    assert 'sphere { <4,2,0>, 3 pigment { color rgb <1,0,0> } }' in result
    assert "location <-8,4,-12>" in result
    assert "rgb <2,1.00392157,0>" in result
    assert result.count("sphere {") == 1  # reference object is preview-only
    assert cp.overlay_pov_scene(source, shot, cp.sample_shot(shot)[0], True).count("sphere {") == 2
    animation = cp.pov_animation_text(shot, source)
    assert "array[49]" in animation
    assert "frame_number-1" in animation
    assert "look_at RD_Target[RD_Index]" in animation


def test_pov_invalid_camera_is_a_clear_error():
    shot = cp.default_shot()
    for source in ["// camera { }", "camera { location <0,0,0>"]:
        with pytest.raises(ValueError):
            cp.overlay_pov_scene(source, shot, cp.sample_shot(shot)[0])


def test_literal_camera_import_and_expression_rejection():
    pose = cp.read_pov_camera('// camera {}\ncamera { location <30,50,-100> look_at <0,10,0> }')
    assert pose == {"location": [30, 50, -100], "look_at": [0, 10, 0]}
    with pytest.raises(ValueError, match="expressions"):
        cp.read_pov_camera('camera { location <X,0,-9> look_at <0,0,0> }')


def test_main_renderer_consumes_director_snapshots(tmp_path):
    from types import SimpleNamespace
    from tkray_tracer import LiveRayTraceViewer
    viewer = LiveRayTraceViewer.__new__(LiveRayTraceViewer)
    viewer.is_rendering = False
    values = {"movie_frames": 3}
    viewer.form = SimpleNamespace(get_values=lambda: values, set_values=values.update)
    viewer.set_status = lambda text: None
    template = tmp_path / "original.pov"
    source = 'camera { location <0,2,-8> look_at <0,1,0> }\nsphere { <0,1,0>, 1 }\n'
    template.write_text(source)
    shot = cp.default_shot()
    viewer.use_director_shot(shot, True, template, False)
    frames = viewer._requested_scene1_frames()
    assert len(frames) == 49 and values["movie_frames"] == 49
    viewer.director_shot["lights"][0]["brightness"] = 99
    output = tmp_path / "frame.pov"
    viewer._write_pov_camera_frame(template, output, frames[24])
    assert "location <0,6,-15>" in output.read_text()
    assert "rgb <1.5,1.5,1.5>" in output.read_text()
    assert template.read_text() == source
    viewer.use_original_camera_path()
    assert viewer.director_shot is None


def test_editor_real_widgets_path_lights_drag_and_playback(tmp_path):
    import tkinter as tk
    from types import SimpleNamespace
    from camera_path_editor import CameraPathEditor

    root = tk.Tk()
    root.withdraw()
    include = tmp_path / "rayincludes.py"
    include.write_text("# Original scenes\n")
    selected = []
    shot = cp.default_shot()
    shot["pov_template"] = None
    editor = CameraPathEditor(root, include, lambda *args: selected.append(args),
                              shot=shot, template_path=tmp_path / "generated.pov")
    editor.withdraw()
    try:
        root.update_idletasks()
        assert editor.template_path is None
        assert not editor.use_existing.get()
        assert len(editor.frames) == 49
        editor.vars["roll"].set("90")
        assert editor.apply()
        assert editor.shot["roll"] == 90
        editor.vars["steps"].set("8")
        editor.vars["kind"].set("Line")
        assert editor.apply()
        assert len(editor.frames) == 9
        editor.add_move()
        assert len(editor.frames) == 33
        editor.vars["target_c"].set("2,1,0")
        assert editor.apply()
        editor.add_light()
        editor.vars["light_color"].set("#00ff80")
        editor.vars["light_brightness"].set("3")
        assert editor.apply()
        editor.place.set("Object")
        editor.dragging = True
        editor.drag(SimpleNamespace(x=100, y=120))
        assert editor.shot["object"]["position"] != [0, 1, 0]
        editor.on_scrub(5)
        assert editor.frame_index == 5
        editor.play()
        assert editor.timer is not None
        editor.stop()
        assert editor.timer is None
        editor.use_path(True)
        assert len(selected) == 1
        assert selected[0][0]["lights"][-1]["color"] == "#00ff80"
        editor.delete_move()
        assert len(editor.shot["segments"]) == 1
        editor.vars["a"].set("bad input")
        assert not editor.apply()
        assert "Check settings" in editor.status.get()
    finally:
        editor.close()
        root.destroy()
