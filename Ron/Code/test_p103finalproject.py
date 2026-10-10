"""Run with: python Ron/Code/test_p103finalproject.py"""
import math
import unittest

import numpy as np

from p103finalproject import ColoredPixel, Cube3d, Line3d, Point3d, Square3d, Vector3d
from p103finalproject import cross, dot, unit_vector


def box(width=2, depth=3, height=4):
    vertices = [Point3d(x, y, z) for z in (0, height)
                for y in (0, depth) for x in (0, width)]
    edges = {}

    def face(indices):
        lines = []
        for start, end in zip(indices, indices[1:] + indices[:1]):
            key = tuple(sorted((start, end)))
            if key not in edges:
                edges[key] = Line3d(vertices[start], vertices[end])
            lines.append(edges[key])
        return Square3d(*lines)

    # Adjacent faces deliberately share the same Line3d objects.
    faces = [face(indices) for indices in (
        [0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4],
        [2, 3, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5])]
    return Cube3d(*faces)


class GeometryTests(unittest.TestCase):
    def assertPoint(self, point, expected):
        np.testing.assert_allclose(point.get_xyz(), expected, atol=1e-10)

    def test_products_for_all_input_type_pairs(self):
        def representations(x, y, z):
            return (Point3d(x, y, z),
                    Line3d(Point3d(10, 20, 30), Point3d(10 + x, 20 + y, 30 + z)),
                    Vector3d(Point3d(-5, 6, -7), Point3d(-5 + x, 6 + y, -7 + z)))

        for u in representations(2, -3, 4):
            for v in representations(-1, 5, 2):
                with self.subTest(u=type(u).__name__, v=type(v).__name__):
                    self.assertEqual(dot(u, v), -9)
                    result = cross(u, v)
                    self.assertIsInstance(result, Vector3d)
                    self.assertPoint(result.get_start(), (0, 0, 0))
                    self.assertPoint(result.get_end(), (-26, -8, 7))
                    self.assertEqual(dot(result, u), 0)
                    self.assertEqual(dot(result, v), 0)
                    self.assertPoint(cross(v, u).get_end(), (26, 8, -7))

    def test_cube_can_generate_faces_from_one_square(self):
        base = box(depth=2)._square1
        cube = Cube3d(base)
        self.assertEqual(cube.get_volume(), 8)
        self.assertPoint(cube.get_center(), (1, 1, 1))
        self.assertEqual(len({cube._square1, cube._square2, cube._square3,
                              cube._square4, cube._square5, cube._square6}), 6)
        # The generated side face reuses the original base corner object.
        self.assertTrue(any(face._line1.get_start() is base._line1.get_start()
                            for face in (cube._square3, cube._square4,
                                         cube._square5, cube._square6)))
        cube.zrot(math.pi / 2, pivot="center")
        self.assertAlmostEqual(cube.get_volume(), 8)

    def test_one_square_and_height_generate_rectangular_box(self):
        base = box()._square1
        rectangular = Cube3d(base, 10)
        self.assertEqual(rectangular.get_volume(), 60)
        self.assertPoint(rectangular.get_center(), (1, 1.5, 5))
        rectangular2 = Cube3d(base, height=10)
        self.assertEqual(rectangular2.get_volume(), 60)

    def test_single_face_constructor_after_tilting_and_color_setters(self):
        base = box(width=5, depth=5)._square1
        base.xrot(0.4).yrot(0.7).move(2, 3, 4)
        cube = Cube3d(base)
        self.assertAlmostEqual(cube.get_volume(), 125)
        self.assertEqual(len({id(p) for p in cube._points()}), 8)
        cube.set_bc('blue')
        cube.set_fc('red')
        self.assertEqual(cube.get_bc(), 'blue')
        self.assertEqual(cube.get_fc(), 'red')
        self.assertIn('Cube3d:', str(cube))
        cube.zrot(0.7, pivot='center')
        self.assertAlmostEqual(cube.get_volume(), 125)

    def test_generated_box_rejects_bad_base_or_height(self):
        base = box()._square1
        for height in (0, float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError):
                Cube3d(base, height)
        with self.assertRaises(ValueError):
            Cube3d(Square3d(Line3d(Point3d(0, 0, 0), Point3d(1, 0, 0)),
                            Line3d(Point3d(1, 0, 0), Point3d(2, 0, 0)),
                            Line3d(Point3d(2, 0, 0), Point3d(3, 0, 0)),
                            Line3d(Point3d(3, 0, 0), Point3d(0, 0, 0))))
        with self.assertRaises(TypeError):
            Cube3d(base, base, base)

    def test_signed_height_ignores_winding_on_each_coordinate_plane(self):
        for axis in range(3):
            others = [i for i in range(3) if i != axis]
            coords = []
            for a, b in ((1, 1), (1, 6), (6, 6), (6, 1)):
                xyz = [5, 5, 5]
                xyz[others[0]], xyz[others[1]] = a, b
                coords.append(xyz)
            for order in (coords, list(reversed(coords))):
                for height in (None, 25, -25):
                    points = [Point3d(*xyz) for xyz in order]
                    base = Square3d(*(Line3d(points[i], points[(i + 1) % 4])
                                      for i in range(4)))
                    cube = Cube3d(base, height=height)
                    depth = 5 if height is None else height
                    for point in cube._square2._points():
                        self.assertAlmostEqual(point.get_xyz()[axis], 5 + depth)
                    self.assertAlmostEqual(cube.get_volume(), 25 * abs(depth))
                    self.assertAlmostEqual(cube.get_center().get_xyz()[axis], 5 + depth / 2)

    def test_tilted_signed_height_is_perpendicular_and_reverses(self):
        base = box(width=5, depth=5)._square1
        base.xrot(0.4).yrot(0.7).move(2, 3, 4)
        positive, negative = Cube3d(base, 7), Cube3d(base, -7)
        origin = np.array(base.get_center().get_xyz())
        offset = np.array(positive._square2.get_center().get_xyz()) - origin
        reverse = np.array(negative._square2.get_center().get_xyz()) - origin
        np.testing.assert_allclose(reverse, -offset, atol=1e-10)
        self.assertAlmostEqual(np.linalg.norm(offset), 7)
        self.assertGreater(offset[np.argmax(np.abs(offset))], 0)
        edge = np.array(base._line1.get_end().get_xyz()) - np.array(base._line1.get_start().get_xyz())
        self.assertAlmostEqual(np.dot(offset, edge), 0)
        self.assertAlmostEqual(negative.get_volume(), 175)

    def test_products_preserve_inputs_and_ignore_line_positions(self):
        u = Line3d(Point3d(10, 20, 30), Point3d(11, 20, 30))
        v = Vector3d(Point3d(7, 8, 9), Point3d(7, 9, 9))
        before = [p.get_xyz() for shape in (u, v) for p in shape._points()]
        self.assertEqual(dot(u, u), 1)
        self.assertEqual(dot(u, v), 0)
        normal = cross(u, v)
        self.assertPoint(normal.get_end(), (0, 0, 1))
        normal.move(5, 6, 7)
        unit_vector(u).move(-2, 3, 1)
        self.assertEqual(before, [p.get_xyz() for shape in (u, v) for p in shape._points()])
        u.move(10, -20, 40)
        v.move(-10, 20, -40)
        self.assertPoint(cross(u, v).get_end(), (0, 0, 1))

    def test_parallel_and_zero_cross_products(self):
        u = Point3d(1, 2, 3)
        for v in (Point3d(2, 4, 6), Point3d(-1, -2, -3), Point3d(0, 0, 0)):
            self.assertPoint(cross(u, v).get_end(), (0, 0, 0))
        self.assertEqual(dot(u, Point3d(0, 0, 0)), 0)

    def test_products_do_not_round_away_small_components(self):
        x = Point3d(0.001, 0, 0)
        y = Point3d(0, 0.001, 0)
        self.assertAlmostEqual(dot(x, x), 0.000001, places=15)
        self.assertAlmostEqual(cross(x, y).get_end().z, 0.000001, places=15)

    def test_unit_vectors_have_correct_direction_and_length(self):
        for value in (Point3d(3, 4, 0),
                      Line3d(Point3d(10, 20, 30), Point3d(13, 24, 30)),
                      Vector3d(Point3d(-10, -20, -30), Point3d(-7, -16, -30))):
            result = unit_vector(value)
            self.assertIsInstance(result, Vector3d)
            self.assertPoint(result.get_start(), (0, 0, 0))
            self.assertPoint(result.get_end(), (0.6, 0.8, 0))
            self.assertAlmostEqual(result.length(), 1)
        for size in (1e-300, 1e308):
            result = unit_vector(Point3d(size, -size, size))
            self.assertAlmostEqual(result.length(), 1)
            self.assertPoint(result.get_end(), (1 / math.sqrt(3), -1 / math.sqrt(3),
                                               1 / math.sqrt(3)))

    def test_vector_helpers_reject_invalid_input(self):
        point = Point3d(1, 0, 0)
        for invalid in (None, 2, (1, 2, 3)):
            for operation in (lambda: dot(invalid, point), lambda: dot(point, invalid),
                              lambda: cross(invalid, point), lambda: cross(point, invalid),
                              lambda: unit_vector(invalid)):
                with self.assertRaises(TypeError):
                    operation()
        for invalid in (Point3d(float('nan'), 0, 0), Point3d(0, float('inf'), 0)):
            for operation in (lambda: dot(point, invalid), lambda: cross(invalid, point),
                              lambda: unit_vector(invalid)):
                with self.assertRaises(ValueError):
                    operation()
        for zero in (Point3d(0, 0, 0),
                     Line3d(Point3d(3, 4, 5), Point3d(3, 4, 5)),
                     Vector3d(Point3d(1, 2, 3), Point3d(1, 2, 3))):
            with self.assertRaises(ValueError):
                unit_vector(zero)

    def test_cross_product_normal_can_drive_rotation(self):
        normal = unit_vector(cross(Point3d(2, 0, 0), Point3d(0, 3, 0)))
        point = Point3d(1, 0, 0)
        point.vecrot(normal, math.pi / 2)
        self.assertPoint(point, (0, 1, 0))

    def test_line_midpoint_and_length(self):
        line = Line3d(Point3d(-1, 2, 3), Point3d(2, 6, 15))
        self.assertEqual(line.length(), 13)
        self.assertPoint(line._center, (0.5, 4, 9))
        self.assertIs(line.move(1, -2, 4), line)
        self.assertPoint(line.get_center(), (1.5, 2, 13))
        line.get_start().set_xyz(0, 0, 0)
        self.assertPoint(line._center, (1.5, 2, 9.5))

    def test_point_rotations_and_subclass_identity(self):
        cases = [('xrot', (1, -3, 2)), ('yrot', (3, 2, -1)),
                 ('zrot', (-2, 1, 3))]
        for method, expected in cases:
            point = ColoredPixel(1, 2, 3, 'red')
            self.assertIs(getattr(point, method)(math.pi / 2), point)
            self.assertPoint(point, expected)
            self.assertEqual(point.get_color(), 'red')
        self.assertIs(point.move(1, 2, 3), point)
        self.assertIs(point.set_xyz(1, 2, 3), point)

    def test_vector_uses_current_line_points(self):
        vector = Vector3d(Point3d(1, 0, 0), Point3d(2, 0, 0))
        origin = vector.get_origin()
        self.assertIs(vector.zrot(math.pi / 2), vector)
        self.assertIs(vector.get_origin(), vector.get_start())
        self.assertPoint(origin, (0, 1, 0))
        self.assertPoint(vector.get_direction(), (0, 2, 0))
        vector.set_origin(Point3d(3, 4, 5))
        vector.set_direction(Point3d(5, 6, 7))
        self.assertPoint(vector._center, (4, 5, 6))
        self.assertIn('3.00', str(vector))

    def test_square_area_and_center_follow_children(self):
        square = box()._square1
        self.assertEqual(square.get_area(), 6)
        self.assertPoint(square._center, (1, 1.5, 0))
        self.assertIs(square.scale(0.5), square)
        self.assertAlmostEqual(square.get_area(), 1.5)
        self.assertPoint(square._center, (0.5, 0.75, 0))
        square._line1.move(0, 0, 4)
        self.assertPoint(square._center, (0.5, 0.75, 1))

    def test_cube_volume_center_and_shared_edges(self):
        cube = box()
        self.assertEqual(cube.get_volume(), 24)
        self.assertPoint(cube._center, (1, 1.5, 2))
        edge = cube._square1._line1
        point = edge.get_start()
        self.assertIs(cube.move(10, 20, 30), cube)
        self.assertPoint(point, (10, 20, 30))
        self.assertPoint(cube.get_center(), (11, 21.5, 32))
        self.assertPoint(edge.get_center(), (11, 20, 30))
        self.assertIs(cube.scale(0.5), cube)
        self.assertPoint(point, (5, 10, 15))
        self.assertAlmostEqual(cube.get_volume(), 3)

    def test_all_shapes_rotate_in_place_without_size_drift(self):
        matrices = {
            'xrot': np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
            'yrot': np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]),
            'zrot': np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])}
        for method, matrix in matrices.items():
            cube = box()
            for shape in (cube._square1._line1, cube._square1, cube):
                before = np.array(shape.get_center().get_xyz())
                self.assertIs(getattr(shape, method)(math.pi / 2), shape)
                self.assertPoint(shape.get_center(), matrix @ before)
                getattr(shape, method)(-math.pi / 2)
            self.assertAlmostEqual(cube.get_volume(), 24)
        cube = box()
        for _ in range(100):
            cube.xrot(0.45).yrot(-0.3).zrot(0.7)
        self.assertAlmostEqual(cube.get_volume(), 24, places=9)

    def test_arbitrary_axis_direction_offset_and_shared_axis(self):
        axis = Line3d(Point3d(1, 2, 0), Point3d(1, 2, 4))
        point = Point3d(2, 2, 3)
        self.assertIs(point.vecrot(axis, math.pi / 2), point)
        self.assertPoint(point, (1, 3, 3))
        cube = box()
        axis = cube._square1._line1
        self.assertIs(cube.vecrot(axis, math.pi / 2), cube)
        self.assertPoint(cube._center, (1, -2, 1.5))
        self.assertPoint(axis.get_end(), (2, 0, 0))
        self.assertAlmostEqual(cube.get_volume(), 24)

    def test_principal_pivots_match_known_rotations(self):
        matrices = {
            'xrot': np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
            'yrot': np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]),
            'zrot': np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])}
        for method, matrix in matrices.items():
            for kind in ('point', 'line', 'vector', 'square', 'cube'):
                for mode in ('center', 'explicit'):
                    with self.subTest(method=method, kind=kind, mode=mode):
                        cube = box().move(3, 5, 7)
                        shape = {'point': ColoredPixel(3, 5, 7, 'red'),
                                 'line': cube._square1._line1,
                                 'vector': Vector3d(Point3d(3, 5, 7), Point3d(5, 5, 7)),
                                 'square': cube._square1, 'cube': cube}[kind]
                        points = [shape] if kind == 'point' else list(
                            {id(p): p for p in shape._points()}.values())
                        before = [np.array(p.get_xyz()) for p in points]
                        center = (shape if kind == 'point' else shape.get_center()).get_xyz()
                        pivot = 'center' if mode == 'center' else Point3d(-2, 1, 4)
                        origin = np.array(center if mode == 'center' else pivot.get_xyz())
                        self.assertIs(getattr(shape, method)(math.pi / 2, pivot=pivot), shape)
                        for point, old in zip(points, before):
                            self.assertPoint(point, origin + matrix @ (old - origin))
                        if kind == 'cube':
                            self.assertAlmostEqual(shape.get_volume(), 24)

    def test_either_line_endpoint_can_stay_fixed(self):
        for endpoint, expected in [('start', ((2, 3, 4), (2, 5, 4))),
                                   ('end', ((4, 1, 4), (4, 3, 4)))]:
            line = Line3d(Point3d(2, 3, 4), Point3d(4, 3, 4))
            pivot = line.get_start() if endpoint == 'start' else line.get_end()
            line.zrot(math.pi / 2, pivot=pivot)
            self.assertPoint(line.get_start(), expected[0])
            self.assertPoint(line.get_end(), expected[1])

    def test_cube_corner_and_coordinate_tuple_pivots(self):
        cube = box().move(10, 20, 30)
        corner = cube._square1._line1.get_start()
        cube.zrot(math.pi / 2, pivot=corner)
        self.assertPoint(corner, (10, 20, 30))
        self.assertPoint(cube.get_center(), (8.5, 21, 32))
        cube.zrot(-math.pi / 2, pivot=(10, 20, 30))
        self.assertPoint(cube.get_center(), (11, 21.5, 32))
        self.assertAlmostEqual(cube.get_volume(), 24)

    def test_vecrot_pivot_overrides_axis_location_but_not_direction(self):
        axis = Line3d(Point3d(9, 8, 7), Point3d(9, 8, 11))
        point = Point3d(3, 3, 4)
        self.assertIs(point.vecrot(axis, math.pi / 2, pivot=(2, 3, 4)), point)
        self.assertPoint(point, (2, 4, 4))
        point.vecrot(axis, 0.7, pivot='center')
        self.assertPoint(point, (2, 4, 4))
        cube = box().move(3, 5, 7)
        before = [np.array(p.get_xyz()) for p in cube._points()]
        center = np.array(cube.get_center().get_xyz())
        matrix = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        self.assertIs(cube.vecrot(axis, math.pi / 2, pivot='center'), cube)
        for point, old in zip(cube._points(), before):
            self.assertPoint(point, center + matrix @ (old - center))
        self.assertPoint(cube.get_center(), center)
        self.assertAlmostEqual(cube.get_volume(), 24)

    def test_centered_rotation_freezes_shared_axis_and_preserves_size(self):
        cube = box().move(3, 5, 7)
        axis = cube._square1._line1
        corner = axis.get_start()
        cube.vecrot(axis, math.pi / 2, pivot='center')
        self.assertPoint(corner, (3, 8.5, 7.5))
        for _ in range(50):
            cube.xrot(0.45, pivot='center').yrot(-0.3, pivot='center')
        self.assertPoint(cube.get_center(), (4, 6.5, 9))
        self.assertAlmostEqual(cube.get_volume(), 24, places=9)

    def test_invalid_pivots_do_not_partially_change_shape(self):
        cube = box()
        before = [p.get_xyz() for p in cube._points()]
        axis = Line3d(Point3d(0, 0, 0), Point3d(0, 0, 1))
        for pivot in ('typo', (1, 2), ((1, 2, 3),), (1, 2, float('nan')),
                      (1, 2, float('inf'))):
            for method in ('xrot', 'yrot', 'zrot', 'vecrot'):
                with self.assertRaises(ValueError):
                    args = (axis, 0.45) if method == 'vecrot' else (0.45,)
                    getattr(cube, method)(*args, pivot=pivot)
                self.assertEqual(before, [p.get_xyz() for p in cube._points()])

    def test_degenerate_shapes_and_invalid_transforms(self):
        self.assertEqual(box(height=0).get_volume(), 0)
        self.assertEqual(box(width=0).get_volume(), 0)
        cube = box()
        before = [point.get_xyz() for point in cube._points()]
        axis = Line3d(Point3d(1, 1, 1), Point3d(1, 1, 1))
        with self.assertRaises(ValueError):
            cube.vecrot(axis, 0.5)
        for factor in (0, -1, 10.1, float('nan')):
            with self.assertRaises(ValueError):
                cube.scale(factor)
        self.assertEqual(before, [point.get_xyz() for point in cube._points()])


if __name__ == '__main__':
    unittest.main()
