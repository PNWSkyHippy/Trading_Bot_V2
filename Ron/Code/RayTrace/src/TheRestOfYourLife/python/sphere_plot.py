# Python port of sphere_plot.cc
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math

from rtweekend import pi, random_double


def main():
    for _i in range(200):
        r1 = random_double()
        r2 = random_double()
        x = math.cos(2 * pi * r1) * 2 * math.sqrt(r2 * (1 - r2))
        y = math.sin(2 * pi * r1) * 2 * math.sqrt(r2 * (1 - r2))
        z = 1 - 2 * r2
        print(x, y, z)


if __name__ == "__main__":
    main()
