from local_functions import colorize

list = [5, 7, "09", 6, "hello"]
list.extend(["x", "x",50])
print(list)
print(dir())
myvar = dir(colorize)
print(myvar, __builtins__)
print(locals())
print(id)
print(hash(colorize))
print(callable(colorize))
print(id(list))
print(locals())
print(globals())
print(repr(print(5*5)))
print(__name__)