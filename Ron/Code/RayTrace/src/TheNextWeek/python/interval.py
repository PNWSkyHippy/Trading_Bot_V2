# Python port of interval.h
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from rtweekend import infinity


class Interval:
    def __init__(self, a=None, b=None):
        if a is None and b is None:
            self.min = +infinity  # Default interval is empty
            self.max = -infinity
        elif isinstance(a, Interval):
            # Create the interval tightly enclosing the two input intervals.
            self.min = a.min if a.min <= b.min else b.min
            self.max = a.max if a.max >= b.max else b.max
        else:
            self.min = a
            self.max = b

    def size(self):
        return self.max - self.min

    def contains(self, x):
        return self.min <= x <= self.max

    def surrounds(self, x):
        return self.min < x < self.max

    def clamp(self, x):
        if x < self.min:
            return self.min
        if x > self.max:
            return self.max
        return x

    def expand(self, delta):
        padding = delta / 2
        return Interval(self.min - padding, self.max + padding)

    def __add__(self, displacement):
        return Interval(self.min + displacement, self.max + displacement)

    def __radd__(self, displacement):
        return self + displacement


Interval.empty = Interval(+infinity, -infinity)
Interval.universe = Interval(-infinity, +infinity)
