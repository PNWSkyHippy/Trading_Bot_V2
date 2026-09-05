from PIL import Image
import os, sys, io
import argparse
import logging
from colors import write_color
from vectors import Vec3

logger = logging.getLogger(__name__)
file_formats = [
                "bmp",  "gif",  "ico", 
                "jpg",  "pcx",  "png", 
                "ppm",  "tga",  "tif"
            ]       


def create_ppm():
    image_width = 256
    image_height = 256
   
    ppm_image = f'P3\n{image_width} {image_height}\n255\n'
    for j in range(image_height):
        logger.debug(f'\rScanlines remaining: {image_height - j} ')
        row_rgb = ""
        for i in range (image_width):
            r = float(i) / (image_width-1)
            g = float(j) / (image_height-1)
            b = 0.0;

            row_rgb += f'{r} {g} {b}\t\t'
        ppm_image += f'{row_rgb}\n'  
    logger.debug(f'\rDone.                 \n')  
    return ppm_image

    
def main():
#    logging.basicConfig(filename='myapp.log', level=logging.INFO)
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(levelname)s: %(message)s"
    )
    
    def wide_formatter(prog):
        return (argparse.RawDescriptionHelpFormatter(prog,width=110,max_help_position=46,))

    parser = argparse.ArgumentParser(
        description="convert ppm tp jpg",
        epilog="""\
Usage examples:
  make_ppm.py -i <input file> -o <output file>
""",
        formatter_class=wide_formatter,
    )

    parser.add_argument("-o", "--outfile", metavar="",
        help="\tpath and name of output file",
    )
    parser.add_argument("-i", "--infile", metavar="",
        help="\tpath and name of output file",
    )
    
    parser.add_argument("-f", "--format", metavar="",
        help="\tfile format to output to",
    )

    parser.add_argument("-l", "--list", action="store_true",
        help="\tlist supported file formats",
    )

    parser.add_argument("-s", "--scale", metavar="",
        help="\ta factor between .1 and 10 to scale the image evenly up/downn",
    )
    

    parser.add_argument("-r", "--resize", metavar="",
        help="\twith/ixesls,height/pixels to resize the image to",
    )
    
    parser.add_argument("-d", "--demo", action="store_true",
        help="\tlist supported file formats",
    )
    
    args = parser.parse_args()
    
    if args.list:
        i = 1
        out_string = ""
        for file in file_formats:
            out_string += f'{file}\t'
            if i % 3 == 0:
                out_string += '\n'
            i += 1
        print(f'Supported Formats:\n{out_string}')
        sys.exit(2)
 
    scale_it = float(args.scale) if args.scale else 1.0
    resize_x = resize_y = 0.0
    if not args.resize:
        resize_x = rsize_y = 0
    else:
        try:
            resize_x, resize_y = args.resize.split(",")
        except:
            raise ValueError(f'Error {args.resize} is not a valid height,width number pair')
        resize_x = float(resize_x)
        resize_y = float(resize_y)
    
    is_demo = args.demo if args.demo else False
                      
    format = args.format if args.format else False
    
      
    infile = args.infile if args.infile else  False
    outfile = args.outfile if args.outfile else False
  
    width, height = args.resize.split(",") if args.resize else (0,0)
 
    is_resize = True if args.resize else False

    is_scaled = True if args.scale else False
    scale_fac = float(args.scale) if args.scale else float(1.0)
    scale_fac = scale_fac if scale_fac >= .1 else .1
    scale_fac = scale_fac if scale_fac <= 10 else 10.0
    
    width = int(width)
    height = int(height)
    
    is_resize - False if is_scaled else is_resize
    
    
    if is_demo and not outfile:
        outfile = "default.ppm"
        format = "ppm"
    if outfile and not format:
        print('Error: When giving an output filename you must include  -f <File Format to create>')
        sys.exit(5)
        
    if (not infile or not outfile) and not is_demo:
        print('Error" You must specify an input and an output file')
        sys.exit(3)
        
    if outfile and (format not in file_formats):   
        raise ValueError(f'Error: {e} format not supported')
  
    out_ext = False
    try:
        f, e = outfile.split(".")
        out_ext = True
    except:
        nut_ext = False
      
    if out_ext:
        f, e = outfile.split(".")
        outfile = f + "." + format
    else:
        outfile = outfile + "." + format
  
    if not is_demo:
        try:
            f, e = infile.split(".")
        except:
            raise ValueError(f'Error {infile} not found')
  
        if infile != outfile:
            with Image.open(infile) as img:
                if is_scaled:
                    width = int(img.width * scale_fac)
                    height = int(img.height * scale_fac)
                    print(f'Original image Width: {img.width}, Height: {img.height}')
                    out = img.resize((width, height))
                    print(f'Converted image Width: {out.width}, Height: {out.height}')
                elif is_resize:
                    print(f'Original image Width: {img.width}, Height: {img.height}')
                    out = img.resize((width, height))
                    print(f'Converted image Width: {out.width}, Height: {out.height}')
                else:
                    # Fallback if is_resize is False so 'out' is always defined
                    out = img
                out.save(outfile)
        except OSError:
            print("cannot convert", infile)

        img = Image.open(outfile)
        img.show()
    else:
        ppm_img = create_ppm()
        ppm_bytes = ppm_img.encode('utf-8') if isinstance(ppm_img, str) else ppm_img
        # 2. Wrap the buffer in an in-memory stream
        ppm_stream = io.BytesIO(ppm_bytes)
        outfile = outfile if outfile else "default.ppm"
        
       try:
            with Image.open(ppm_stream) as img:
                if is_scaled:
                    width = int(img.width * scale_fac)
                    height = int(img.height * scale_fac)
                    print(f'Original image Width: {img.width}, Height: {img.height}')
                    out = img.resize((width, height))
                    print(f'Converted image Width: {out.width}, Height: {out.height}')
                elif is_resize:
                    print(f'Original image Width: {img.width}, Height: {img.height}')
                    out = img.resize((width, height))
                    print(f'Converted image Width: {out.width}, Height: {out.height}')
                else:
                    # Fallback if is_resize is False so 'out' is always defined
                    out = img
                out.save(outfile)
        except OSError:
            print("cannot convert", infile)
        im = Image.open(outfile)
        im.show()


if __name__ == "__main__":
    main()
        