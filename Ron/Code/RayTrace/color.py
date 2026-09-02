#ifndef COLOR_H
#define COLOR_H

from vector import Vec3



color = Vec3()

def write_color(outfile, pixel_color):
    r = pixel_color.x();
    g = pixel_color.y();
    b = pixel_color.z();

    ## Translate the [0,1] component values to the byte range [0,255].
    rbyte = int(255.999 * r);
    gbyte = int(255.999 * g);
    bbyte = int(255.999 * b);

    #Write out the pixel color components.
    try:
        # 3. Open it from memory and save it natively
        with Image.open(ppm_stream) as img:
            img.save(outfile, optimize=True)
            # Automatically converts and saves to disk
    except:
        raise ValueError("Error saving output file")
#    print(f'{rbyte} {gbyte} {bbyte}\n')
    
def main():
    return

if __name__ == "__main__":
    main()
#endif