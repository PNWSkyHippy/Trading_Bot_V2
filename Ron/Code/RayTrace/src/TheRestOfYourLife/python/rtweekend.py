# Python port of rtweekend.h
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math
import random

# Constants

infinity = math.inf
pi = 3.1415926535897932385


# Utility Functions


def degrees_to_radians(degrees):
    return degrees * pi / 180.0


def random_double(min_val=None, max_val=None):
    # Returns a random real in [0,1), or [min_val, max_val) if both bounds are given.
    if min_val is None:
        return random.random()
    return min_val + (max_val - min_val) * random.random()


def random_int(min_val, max_val):
    # Returns a random integer in [min_val, max_val].
    return int(random_double(min_val, max_val + 1))
