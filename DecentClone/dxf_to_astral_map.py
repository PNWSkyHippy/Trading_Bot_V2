#!/usr/bin/env python
"""Convert simple AutoCAD DXF tunnel splines into an Astral Drift .map file.

Expected DXF layers:
  TUNNEL_MAIN     - playable main tunnel spline(s)
  TUNNEL_BRANCH   - branch tunnel spline(s)
  TUNNEL_PORTALS  - LINE entities linking portal endpoints
  TUNNEL_META     - optional TEXT notes such as "1way"
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RADIUS = 120.0
DEFAULT_WALL_TEXTURE_ID = "rock060"
DEFAULT_RIB_COLOR = "#21c7c0"


@dataclass
class Entity:
    type: str
    layer: str
    pairs: list[tuple[int, str]]


def vec_sub(a: dict, b: dict) -> dict:
    return {"x": a["x"] - b["x"], "y": a["y"] - b["y"], "z": a["z"] - b["z"]}


def vec_dot(a: dict, b: dict) -> float:
    return a["x"] * b["x"] + a["y"] * b["y"] + a["z"] * b["z"]


def vec_cross(a: dict, b: dict) -> dict:
    return {
        "x": a["y"] * b["z"] - a["z"] * b["y"],
        "y": a["z"] * b["x"] - a["x"] * b["z"],
        "z": a["x"] * b["y"] - a["y"] * b["x"],
    }


def vec_len(v: dict) -> float:
    return math.sqrt(vec_dot(v, v))


def vec_norm(v: dict, fallback: dict | None = None) -> dict:
    length = vec_len(v)
    if length < 1e-9:
        return dict(fallback or {"x": 0.0, "y": 0.0, "z": 1.0})
    return {"x": v["x"] / length, "y": v["y"] / length, "z": v["z"] / length}


def distance(a: dict, b: dict) -> float:
    return vec_len(vec_sub(a, b))


def build_basis(from_point: dict, to_point: dict) -> tuple[dict, dict, dict]:
    forward = vec_norm(vec_sub(to_point, from_point))
    world_up = {"x": 0.0, "y": 1.0, "z": 0.0}
    right = vec_norm(vec_cross(world_up, forward), {"x": 1.0, "y": 0.0, "z": 0.0})
    down = vec_norm(vec_cross(forward, right), {"x": 0.0, "y": -1.0, "z": 0.0})
    return forward, right, down


def read_dxf_pairs(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(errors="ignore").splitlines()
    pairs: list[tuple[int, str]] = []
    for i in range(0, len(lines) - 1, 2):
        try:
            code = int(lines[i].strip())
        except ValueError:
            continue
        pairs.append((code, lines[i + 1].strip()))
    return pairs


def parse_entities(path: Path) -> list[Entity]:
    pairs = read_dxf_pairs(path)
    entities: list[Entity] = []
    in_entities = False
    current_type: str | None = None
    current_pairs: list[tuple[int, str]] = []

    def flush_current() -> None:
        nonlocal current_type, current_pairs
        if not current_type:
            return
        layer = next((value for code, value in current_pairs if code == 8), "")
        entities.append(Entity(current_type, layer, current_pairs))
        current_type = None
        current_pairs = []

    for code, value in pairs:
        if code == 0 and value == "SECTION":
            continue
        if code == 2 and value == "ENTITIES":
            in_entities = True
            continue
        if not in_entities:
            continue
        if code == 0:
            if value == "ENDSEC":
                flush_current()
                break
            flush_current()
            current_type = value
            current_pairs = []
            continue
        if current_type:
            current_pairs.append((code, value))

    flush_current()
    return entities


def collect_triplets(entity: Entity, x_code: int, y_code: int, z_code: int) -> list[tuple[float, float, float]]:
    xs = [float(value) for code, value in entity.pairs if code == x_code]
    ys = [float(value) for code, value in entity.pairs if code == y_code]
    zs = [float(value) for code, value in entity.pairs if code == z_code]
    return list(zip(xs, ys, zs))


def transform_point(raw: tuple[float, float, float], scale: float, offset: tuple[float, float, float]) -> dict:
    x, y, z = raw
    ox, oy, oz = offset
    return {
        "x": (x - ox) * scale,
        "y": (z - oz) * scale,
        "z": (y - oy) * scale,
    }


def dedupe_points(points: list[dict], min_spacing: float = 12.0) -> list[dict]:
    cleaned: list[dict] = []
    for point in points:
        if not cleaned or distance(cleaned[-1], point) >= min_spacing:
            cleaned.append(point)
    if len(cleaned) > 2 and distance(cleaned[0], cleaned[-1]) < min_spacing:
        cleaned[-1] = cleaned[0]
    return cleaned


def densify_points(points: list[dict], max_step: float) -> list[dict]:
    if len(points) < 2:
        return points
    output = [points[0]]
    for start, end in zip(points, points[1:]):
        dist = distance(start, end)
        steps = max(1, math.ceil(dist / max_step))
        for step in range(1, steps + 1):
            t = step / steps
            output.append({
                "x": start["x"] + (end["x"] - start["x"]) * t,
                "y": start["y"] + (end["y"] - start["y"]) * t,
                "z": start["z"] + (end["z"] - start["z"]) * t,
            })
    return output


def make_segment(start: dict, end: dict, kind: str, branch: bool, rib_color: str) -> dict | None:
    length = distance(start, end)
    if length < 8:
        return None
    forward, right, down = build_basis(start, end)
    return {
        "from": start,
        "to": end,
        "kind": kind,
        "length": length,
        "radius": DEFAULT_RADIUS,
        "forward": forward,
        "right": right,
        "down": down,
        "branch": branch,
        "branchMouth": branch,
        "generated": True,
        "wallTextureId": DEFAULT_WALL_TEXTURE_ID,
        "ribColor": rib_color,
    }


def nearest_segment_frame(point: dict, segments: list[dict]) -> dict:
    best = min(
        segments,
        key=lambda seg: min(distance(point, seg["from"]), distance(point, seg["to"])),
    )
    return {
        "point": point,
        "forward": best["forward"],
        "right": best["right"],
        "down": best["down"],
        "radius": DEFAULT_RADIUS,
    }


def convert_dxf(path: Path, scale: float, max_step: float) -> dict:
    entities = parse_entities(path)
    route_entities = [
        entity
        for entity in entities
        if entity.type == "SPLINE" and entity.layer in {"TUNNEL_MAIN", "TUNNEL_BRANCH"}
    ]
    raw_points = [
        point
        for entity in route_entities
        for point in collect_triplets(entity, 10, 20, 30)
    ]
    if len(raw_points) < 2:
        raise SystemExit("No TUNNEL_MAIN/TUNNEL_BRANCH spline points found in DXF.")

    offset = (
        sum(point[0] for point in raw_points) / len(raw_points),
        sum(point[1] for point in raw_points) / len(raw_points),
        sum(point[2] for point in raw_points) / len(raw_points),
    )

    segments: list[dict] = []
    for entity in route_entities:
        branch = entity.layer == "TUNNEL_BRANCH"
        raw_spline = collect_triplets(entity, 10, 20, 30)
        points = [transform_point(point, scale, offset) for point in raw_spline]
        points = densify_points(dedupe_points(points), max_step)
        rib_color = "#f3a329" if branch else DEFAULT_RIB_COLOR
        kind = "branch-acad" if branch else "acad-spline"
        for start, end in zip(points, points[1:]):
            segment = make_segment(start, end, kind, branch, rib_color)
            if segment:
                segments.append(segment)

    if not segments:
        raise SystemExit("DXF splines parsed, but no usable segments were produced.")

    text_notes = " ".join(
        value
        for entity in entities
        if entity.layer == "TUNNEL_META"
        for code, value in entity.pairs
        if code in {1, 3}
    ).lower()
    portals = []
    one_way = "1way" in text_notes or "oneway" in text_notes or "one way" in text_notes
    for index, entity in enumerate(
        entity for entity in entities if entity.type == "LINE" and entity.layer == "TUNNEL_PORTALS"
    ):
        starts = collect_triplets(entity, 10, 20, 30)
        ends = collect_triplets(entity, 11, 21, 31)
        if not starts or not ends:
            continue
        start = transform_point(starts[0], scale, offset)
        end = transform_point(ends[0], scale, offset)
        portals.append({
            "id": f"acad-portal-{index + 1}",
            "label": f"ACAD Portal {index + 1}",
            "entry": nearest_segment_frame(start, segments),
            "exit": nearest_segment_frame(end, segments),
            "oneWay": one_way,
        })

    last = segments[-1]
    return {
        "defaultWallTextureId": DEFAULT_WALL_TEXTURE_ID,
        "defaultRibColor": DEFAULT_RIB_COLOR,
        "segments": segments,
        "portals": portals,
        "targets": [],
        "sentries": [],
        "cursor": last["to"],
        "forward": last["forward"],
        "right": last["right"],
        "down": last["down"],
        "bendDeg": 5,
        "bendRollDeg": 0,
        "radius": DEFAULT_RADIUS,
        "source": {
            "format": "dxf",
            "file": path.name,
            "scale": scale,
            "maxStep": max_step,
            "note": "Converted from TUNNEL_MAIN/TUNNEL_BRANCH splines.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert ACadMap1.dxf into an Astral Drift .map JSON file.")
    parser.add_argument("input", nargs="?", default="ACadMap1.dxf", help="DXF file path")
    parser.add_argument("-o", "--output", default="ACadMap1_converted.map", help="output .map file")
    parser.add_argument(
        "--bundle",
        default="data/map_library_bundle.json",
        help="also write a localhost bootstrap map-library bundle; use '' to skip",
    )
    parser.add_argument("--name", default="ACadMap1 Converted", help="display name for bundled map")
    parser.add_argument("--scale", type=float, default=3.0, help="DXF unit to game unit scale")
    parser.add_argument("--max-step", type=float, default=160.0, help="maximum generated segment length")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        input_path = Path(__file__).resolve().parent / args.input
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent / output_path

    tunnel_map = convert_dxf(input_path, args.scale, args.max_step)
    output_path.write_text(json.dumps(tunnel_map, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")
    print(f"Segments: {len(tunnel_map['segments'])}")
    print(f"Portals: {len(tunnel_map['portals'])}")

    if args.bundle:
        bundle_path = Path(args.bundle)
        if not bundle_path.is_absolute():
            bundle_path = Path(__file__).resolve().parent / bundle_path
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        map_id = "acad-map-1-converted"
        bundle = {
            "version": 1,
            "exportedAt": "2026-06-25T00:00:00.000Z",
            "origin": "DecentClone/dxf_to_astral_map.py",
            "library": [{
                "id": map_id,
                "name": args.name,
                "savedAt": "2026-06-25T00:00:00.000Z",
                "segmentCount": len(tunnel_map["segments"]),
            }],
            "namedMaps": {map_id: tunnel_map},
            "autosave": None,
        }
        bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        print(f"Wrote {bundle_path}")


if __name__ == "__main__":
    main()
