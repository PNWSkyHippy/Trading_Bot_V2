# Python port of integrate_x_sq.cc
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from rtweekend import random_double


def icd(d):
    return 8.0 * pow(d, 1.0 / 3.0)


def pdf(x):
    return (3.0 / 8.0) * x * x


def main():
    n = 1
    total = 0.0

    for _i in range(n):
        z = random_double()
        if z == 0.0:
            continue
        x = icd(z)
        total += x * x / pdf(x)

    print(f"I = {total / n:.12f}")


if __name__ == "__main__":
    main()
