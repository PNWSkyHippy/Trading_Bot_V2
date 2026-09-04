# Python port of pi.cc
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from rtweekend import random_double


def main():
    inside_circle = 0
    inside_circle_stratified = 0
    sqrt_n = 1000

    for i in range(sqrt_n):
        for j in range(sqrt_n):
            x = random_double(-1, 1)
            y = random_double(-1, 1)
            if x * x + y * y < 1:
                inside_circle += 1

            x = 2 * ((i + random_double()) / sqrt_n) - 1
            y = 2 * ((j + random_double()) / sqrt_n) - 1
            if x * x + y * y < 1:
                inside_circle_stratified += 1

    print(f"Regular    Estimate of Pi = {(4.0 * inside_circle) / (sqrt_n * sqrt_n):.12f}")
    print(
        f"Stratified Estimate of Pi = {(4.0 * inside_circle_stratified) / (sqrt_n * sqrt_n):.12f}"
    )


if __name__ == "__main__":
    main()
