import math


class Vec3:
    """3D vector class"""
    
    def __init__(self, e0=0.0, e1=0.0, e2=0.0):
        self.e = [e0, e1, e2]
    
    def x(self):
        return self.e[0]
    
    def y(self):
        return self.e[1]
    
    def z(self):
        return self.e[2]
    
    def value(self):
        return self.e
    
    def __neg__(self):
        return Vec3(-self.e[0], -self.e[1], -self.e[2])
    
    def __getitem__(self, i):
        return self.e[i]
    
    def __setitem__(self, i, value):
        self.e[i] = value
    
    def __iadd__(self, v):
        self.e[0] += v.e[0]
        self.e[1] += v.e[1]
        self.e[2] += v.e[2]
        return self
    
    def __imul__(self, t):
        self.e[0] *= t
        self.e[1] *= t
        self.e[2] *= t
        return self
    
    def __itruediv__(self, t):
        return self.__imul__(1 / t)
    
    def length(self):
        return math.sqrt(self.length_squared())
    
    def length_squared(self):
        return self.e[0] * self.e[0] + self.e[1] * self.e[1] + self.e[2] * self.e[2]
    
    def __str__(self):
        return f"{self.e[0]} {self.e[1]} {self.e[2]}"
    
    def __repr__(self):
        return f"Vec3({self.e[0]}, {self.e[1]}, {self.e[2]})"
    
    def __add__(self, v):
        return Vec3(self.e[0] + v.e[0], self.e[1] + v.e[1], self.e[2] + v.e[2])
    
    def __sub__(self, v):
        return Vec3(self.e[0] - v.e[0], self.e[1] - v.e[1], self.e[2] - v.e[2])
    
    def __mul__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.e[0] * other.e[0], self.e[1] * other.e[1], self.e[2] * other.e[2])
        else:
            return Vec3(self.e[0] * other, self.e[1] * other, self.e[2] * other)
    
    def __rmul__(self, t):
        return Vec3(t * self.e[0], t * self.e[1], t * self.e[2])
    
    def __truediv__(self, t):
        return Vec3((1 / t) * self.e[0], (1 / t) * self.e[1], (1 / t) * self.e[2])


# point3 is just an alias for Vec3, but useful for geometric clarity in the code.
Point3 = Vec3


# Vector Utility Functions

def dot(u, v):
    """Compute dot product of two vectors"""
    return u.e[0] * v.e[0] + u.e[1] * v.e[1] + u.e[2] * v.e[2]


def cross(u, v):
    """Compute cross product of two vectors"""
    return Vec3(u.e[1] * v.e[2] - u.e[2] * v.e[1],
                u.e[2] * v.e[0] - u.e[0] * v.e[2],
                u.e[0] * v.e[1] - u.e[1] * v.e[0])


def unit_vector(v):
    """Compute unit vector in the direction of v"""
    return v / v.length()


def main():
    return

if __name__ == "__main__":
    main()

