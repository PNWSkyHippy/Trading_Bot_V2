from PIL import Image
import os, sys, io
import argparse
import logging
from color import write_color
from vector import Vec3

logger = logging.getLogger(__name__)
file_formats = [
                "bmp",  "gif",  "ico", 
                "jpg",  "pcx",  "png", 
                "ppm",  "tga",  "tif"
            ]       

def create_ppm(outfile):
    image_width = 256
    image_height = 256
    ppm_img = ""
    color = Vec3
    ppm_image = f'P3\n{image_width} {image_height}\n255\n'
    for j in range(image_height):
        logger.info(f'\rScanlines remaining: {image_height - j} ')
        row_rgb = ""
        for i in range (image_width):
            pixel_color =  color(float(i) / (image_width-1),
                                    float(j) / (image_height-1),
                                    0.0
                                )

            ir = int(255.999 * (float(i) / (image_width-1)))
            ig = int(255.999 * (float(j) / (image_height-1)))
            ib = int(255.999 * 0.0)

            row_rgb += f'{ir} {ig} {ib}\t\t'
            if (i+1) % 3 == 0:
                row_rgb += f'{row_rgb}\n'
    
        ppm_img += row_rgb 
    ppm_bytes = ppm_img.encode('utf-8') if isinstance(ppm_img, str) else ppm_img
    # 2. Wrap the buffer in an in-memory stream
    ppm_stream = io.BytesIO(ppm_bytes)
    outfile = outfile if outfile else sys.stdout
    try:
        # 3. Open it from memory and save it natively
        with Image.open(ppm_stream) as img:
            img.save(outfile, optimize=True)
            # Automatically converts and saves to disk
    except:
        raise ValueError("Error saving output file")
    
    logger.info(f'\rDone.                 \n')  
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
  
    if outfile and not format:
        print('Error: When giving an output filename you must include  -f <File Format to create>')
        sys.exit(5)
        
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
        im = Image.open(outfile)
        im.show()
    else:
        ppm_img = create_ppm(outfile)
 #       im = Image.open(outfile)
        im.show()

if __name__ == "__main__":
    main()
    