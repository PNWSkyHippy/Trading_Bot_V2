from PIL import Image
import os, sys, io
import argparse
import logging

logger = logging.getLogger("stdout"
                           )
file_formats = [
                "bmp",  "gif",  "ico", 
                "jpeg", "pcx",  "png", 
                "ppm",  "tga",  "tiff"
            ]       

def roll(im: Image.Image, delta: int) -> Image.Image:
    """Roll an image sideways."""
    xsize, ysize = im.size

    delta = delta % xsize
    if delta == 0:
        return im

    part1 = im.crop((0, 0, delta, ysize))
    part2 = im.crop((delta, 0, xsize, ysize))
    im.paste(part1, (xsize - delta, 0, xsize, ysize))
    im.paste(part2, (0, 0, xsize - delta, ysize))

    return im

def merge(im1: Image.Image, im2: Image.Image) -> Image.Image:
    w = im1.size[0] + im2.size[0]
    h = max(im1.size[1], im2.size[1])
    im = Image.new("RGBA", (w, h))

    im.paste(im1)
    im.paste(im2, (im1.size[0], 0))

    return im

def resize_image(img: Image.Image, height, width) -> Image.Image:
    out = img.resize(height, width)
    return out

def transpose_image(img: Image.Image, direction) -> Image.Image:
    """ Call with direction FLIP_LEFT_RIGHT, FLIP_TOP_BOTTOM, 
        ROTATE_90, ROTATE_180 or ROTATE_270
    """  
    out = img.transpose(direction)
    return out

def rotate_image(img: Image.Image, angle) -> Image.Image:
    """ Rotate image angle defrees couter clockwise """
    out = img.rotate(angle)
    return out

def create_ppm():
    image_width = 256
    image_height = 256
   
    ppm_image = f'P3\n{image_width} {image_height}\n255\n'
    for j in range(image_height):
        logger.info(f'\rScanlines remaining: {image_height - j} ')
        row_rgb = ""
        for i in range (image_width):
            r = float(i) / (image_width-1)
            g = float(j) / (image_height-1)
            b = 0.0;

            ir = int(255.999 * r)
            ig = int(255.999 * g)
            ib = int(255.999 * b)

            row_rgb += f'{ir} {ig} {ib}\t\t'
        ppm_image += f'{row_rgb}\n'  
    logger.info(f'\rDone.                 \n')  
    return ppm_image
    
def main():

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
 
    is_demo = args.demo if args.demo else False
                      
    format = args.format if args.format else False
    
    infile = args.infile if args.infile else  False
    outfile = args.outfile if args.outfile else False
  
    if (not infile or not outfile) and not is_demo:
        print('Error" You must specify an input and an output file')
        sys.exit(3)
        
    if not is_demo and outfile and (format not in file_formats):   
        raise ValueError(f'Error: {e} format not supported')
    if not is_demo:
        try:
            f, e = infile.split(".")
        except:
            raise ValueError(f'Error {infile} not found')
 
        outfile = f + "." + format
        if infile != outfile:
            try:
                with Image.open(infile) as im:
                    im.save(outfile)
            except OSError:
                print("cannot convert", infile)
    else:
        ppm_img = create_ppm()
        # 1. Convert your string buffer to bytes (if it isn't already bytes)
        ppm_bytes = ppm_img.encode('utf-8') if isinstance(ppm_img, str) else ppm_img
        # 2. Wrap the buffer in an in-memory stream
        ppm_stream = io.BytesIO(ppm_bytes)
        outfile = outfile if outfile else "mytest.ppm"
        try:
            # 3. Open it from memory and save it natively
            with Image.open(ppm_stream) as img:
                img.save(outfile, optimize=True)
                # Automatically converts and saves to disk
        except:
            raise ValueError("Error saving output file")
        im = Image.open(outfile)
        im.show()

if __name__ == "__main__":
    main()

