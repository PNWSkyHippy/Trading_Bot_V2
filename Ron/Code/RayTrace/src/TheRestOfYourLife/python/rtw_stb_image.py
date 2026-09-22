# Python port of rtw_stb_image.h
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import os
import sys

from external.stb_image import STBI_FREE, stbi_loadf


class RtwImage:
    bytes_per_pixel = 3

    def __init__(self, image_filename=None):
        self.fdata = None
        self.bdata = None
        self.image_width = 0
        self.image_height = 0
        self.bytes_per_scanline = 0

        if image_filename is None:
            return

        # Hunt for the image file in some likely locations.
        filename = str(image_filename)
        imagedir = os.environ.get("RTW_IMAGES")

        if imagedir and self.load(os.path.join(imagedir, image_filename)):
            return
        if self.load(filename):
            return
        if self.load(os.path.join("images", filename)):
            return
        if self.load(os.path.join("..", "images", filename)):
            return
        if self.load(os.path.join("..", "..", "images", filename)):
            return
        if self.load(os.path.join("..", "..", "..", "images", filename)):
            return
        if self.load(os.path.join("..", "..", "..", "..", "images", filename)):
            return
        if self.load(os.path.join("..", "..", "..", "..", "..", "images", filename)):
            return
        if self.load(
            os.path.join("..", "..", "..", "..", "..", "..", "images", filename)
        ):
            return

        sys.stderr.write(f"ERROR: Could not load image file '{image_filename}'.\n")

    def load(self, filename):
        loaded = stbi_loadf(filename, self.bytes_per_pixel)
        if loaded is None:
            return False
        self.fdata, self.image_width, self.image_height, _n = loaded
        self.bytes_per_scanline = self.image_width * self.bytes_per_pixel
        self.convert_to_bytes()
        return True

    def width(self):
        return 0 if self.fdata is None else self.image_width

    def height(self):
        return 0 if self.fdata is None else self.image_height

    def pixel_data(self, x, y):
        # Return the three RGB bytes of the pixel at x,y. If there is no image data, returns magenta.
        magenta = (255, 0, 255)
        if self.bdata is None:
            return magenta

        x = self.clamp(x, 0, self.image_width)
        y = self.clamp(y, 0, self.image_height)
        i = y * self.bytes_per_scanline + x * self.bytes_per_pixel
        return self.bdata[i], self.bdata[i + 1], self.bdata[i + 2]

    @staticmethod
    def clamp(x, low, high):
        if x < low:
            return low
        if x < high:
            return x
        return high - 1

    @staticmethod
    def float_to_byte(value):
        if value <= 0.0:
            return 0
        if 1.0 <= value:
            return 255
        return int(256.0 * value)

    def convert_to_bytes(self):
        total_bytes = self.image_width * self.image_height * self.bytes_per_pixel
        self.bdata = bytearray(total_bytes)
        for i in range(total_bytes):
            self.bdata[i] = self.float_to_byte(self.fdata[i])
