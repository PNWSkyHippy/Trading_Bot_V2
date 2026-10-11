from class3d import *
from overloaded_inc  import *

def main():
    point25 = Point3d(0,0,0)
    point26 = Point3d(0,0,1)
    point1 = Point3d(1, 1, 1)
    point2 = Point3d(1, 6, 1)
    point3 = Point3d(1, 6, 1)
    point_mul = point2 * point3
    vector1 = Vector3d(point3, point1)
    plane1 = Plane3d(vector1)
    print(plane1)
    point4 = Point3d(6, 6, 1)
    point5 = Point3d(6, 6, 1)
    point6 = Point3d(6, 1, 1)
    point7 = Point3d(6, 1, 1)
    point8 = Point3d(1, 1, 1)
    point21 = (point2 + point3) * point8
    print(f'point21:\n{point21}')
    print(f'point4:  {point4}')
    print(f'point2 * point3 =  : {point_mul}')
    point_mul *= point4
    print(f'point_nul *= point4 =: {point_mul}')
    print(f'degtorad 360 {degtorad(360)}, radtodeg 7 {radtodeg(7)}')
    vec1 = Vector3d(point2, point6)
    print(f'vec1: {vec1}')
    vec1.yrot(.35)
    print(f'vec1 after rotation: {vec1}')

    circle1 = Circle3d(point25, point26, bc="red", fc="green")
    print(circle1)
    cylinder1 = Cylinder3d(point25, point26, 25, bc="blue", fc="yellow")
    print(cylinder1)
    cone1 =  Cone3d(point25, point26, 25, bc="blue", fc="yellow")
    #cone2 = cone1.xrot(degtorad(90))
    #print(cone1)
    red_pixel = ColoredPixel(1, 1, 0, "red")
    print(f'Orig redpixel= {red_pixel}')
    red_pixel.set_color("blue")
    red_pixel.move(1, 1, 1)
    red_pixel.set_x(5)
    print(f'redpixel after set_color blue, move 1 1 1 setx 5 = {red_pixel}')
    line1 = Line3d(point1, point2)
    line2 = Line3d(point3, point4)
    line3 = Line3d(point5, point6)
    line4 = Line3d(point7, point8)
    line5 = Line3d((4,4,4), (4,4,-4))
    line6 = Line3d((4,4,-4),(4,-4,-4))
    line7 = Line3d((4,-4,-4), (4,-4,4))
    line8 = Line3d((4,-4,4),(4,4,4))
    
    cube_sqr = Square3d(line5, line6, line7, line8)
    cube2 = Cube3d(cube_sqr)
    Rectangle3d = Cube3d
    #breakpoint()
    rectangle1 = Rectangle3d(cube_sqr, 100, name="rectangle")
    print(rectangle1)
    print(f'Frseh Made cube2: \n{cube2}')
    cube2.yrot(degtorad(90), pivot="center")
    print(f'cube2 rotated 90 aroud y of center:\n{cube2}')
    square1 = Square3d(line1, line2, line3, line4)
    cube1 = Cube3d(square1)
    rectangle1 = Cube3d(square1, 50, name="Rectangle3d")
    sphere1 = Sphere3d(Point3d(10,10,10), 50,name="sphere1", color="blue")

 #   sphere2 = sphere1.xrot(.5)
    print(point1)
    print(red_pixel)
    print(line1)
    print(f'square1:\n{square1}')
    square1.zrot(.70)
    print(f'square1 rotated around z by .70 radians = {square1}')
    print(f'cuba1 before rotate\n{cube1}')
    cube1.zrot(degtorad(90), Point3d(-10,-10,-10))
    print(f'cube1 rotated 90 deg arund z of its oqn center\n {cube1}')
    print(rectangle1)
    print(sphere1)
 
    print(f'Current center: {square1.get_center()}')

    # --- Example Usage ---
    angle = 0.45  # Angle in radians

    # 1. Representing a 3D Line: Line = Point + t * Vector
    line_point = line2
    line_vector =  line4

    print(f'line2: {line2}  line3 {line3}')
    # Save text only when a before/after comparison is wanted.
    before_line2 = str(line2)
    before_line3 = str(line3)
    line2.xrot(angle)
    line3.vecrot(line1, angle)

    print(f'line2: {line2} line3 {line3}')
    # --- Example Usage ---
    angle = 0.45
    arbitrary_axis = line3 # Diagonal axis
    sample_point = point7

    print("Original Point      :", point2)
    print("Rotated around Y    :", point2.yrot(angle))
    print("Rotated around Z    :", point3.zrot(angle))
    print("Rotated around Vector:", point4.vecrot(arbitrary_axis, angle))


    # --- Output Verification ---
    print("--- ROTATED LINE ---")
    print(f"Original Line : {before_line2}  -> Rotated: {line2}")
    print(f"Original Line: {before_line3}  -> Rotated: {line3}\n")

    #print("--- ROTATED PLANE ---")
    #print(f"Original Point : {plane_point}  -> Rotated: {plane_point_rot}")
    #print(f"Original Vector 1: {plane_v1}  -> Rotated: {plane_v1_rot}")
    #p#rint(f"Original Vector 2: {plane_v2}  -> Rotated: {plane_v2_rot}")

if __name__ == "__main__":
    main()