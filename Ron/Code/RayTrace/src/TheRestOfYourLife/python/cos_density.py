# Python port of cos_density.cc
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from rtweekend import pi
from vec3 import random_cosine_direction


def f(d):
    cos_theta = d.z()
    return cos_theta * cos_theta * cos_theta


def pdf(d):
    return d.z() / pi


def main():
    n = 1000000
    total = 0.0
    for _i in range(n):
        d = random_cosine_direction()
        total += f(d) / pdf(d)

    print(f"PI/2 = {pi / 2.0:.12f}")
    print(f"Estimate = {total / n:.12f}")


if __name__ == "__main__":
    main()
