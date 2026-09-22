# ifndef COLOR_H
# define COLOR_H

from vectors import Vec3


Color = Vec3


def write_color(out, pixel_color: Color) -> None:
    r = pixel_color.x
    g = pixel_color.y
    b = pixel_color.z
    # Translate [0,1] to byte range [0,255]
    rbyte = int(255.999 * r)
    gbyte = int(255.999 * g)
    bbyte = int(255.999 * b)
    # Write out (works with open files or sys.stdout)
    out.write(f"{rbyte} {gbyte} {bbyte}\n")


Color = Vec3


def write_color(pixel_color):
    r = pixel_color.x()
    g = pixel_color.y()
    b = pixel_color.z()
    ## Translate the [0,1] component values to the byte range [0,255].
    rbyte = int(255.999 * r)
    gbyte = int(255.999 * g)
    bbyte = int(255.999 * b)
    print(f"{rbyte} {gbyte} {bbyte}\n")


def main():
    return


if __name__ == "__main__":
    main()
# endif
