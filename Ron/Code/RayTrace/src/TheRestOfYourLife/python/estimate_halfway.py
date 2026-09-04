# Python port of estimate_halfway.cc
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math

from rtweekend import pi, random_double


class Sample:
    def __init__(self, x=0.0, p_x=0.0):
        self.x = x
        self.p_x = p_x


def main():
    n = 10000
    samples = [Sample() for _i in range(n)]
    total = 0.0

    for i in range(n):
        x = random_double(0, 2 * pi)
        sin_x = math.sin(x)
        p_x = math.exp(-x / (2 * pi)) * sin_x * sin_x
        total += p_x
        samples[i] = Sample(x, p_x)

    samples.sort(key=lambda s: s.x)

    half_sum = total / 2.0
    halfway_point = 0.0
    accum = 0.0
    for i in range(n):
        accum += samples[i].p_x
        if accum >= half_sum:
            halfway_point = samples[i].x
            break

    print(f"Average = {total / n:.12f}")
    print(f"Area under curve = {2 * pi * total / n:.12f}")
    print(f"Halfway = {halfway_point:.12f}")


if __name__ == "__main__":
    main()
