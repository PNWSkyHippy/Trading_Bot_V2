"""Example: a Python program that writes turtle commands (a Koch snowflake + a parabola),
then hands them to the viewer's turtle system.  Run:  python gen_example.py  ->  generated.logo
Open it in the viewer with File > Run turtle script, or:  python ../commands3d.py  / turtle generated.logo"""
lines = ["pensize 0.3", "color cyan", "detail 6"]


def koch(n, size):
    if n == 0:
        lines.append(f"fd {size}")
        return
    for turn in (60, -120, 60, 0):
        koch(n - 1, size / 3)
        if turn:
            lines.append(f"lt {turn}")


for _ in range(3):
    koch(3, 30)
    lines.append("rt 120")
lines += ["pu", "color red"]
for x in range(-10, 11):                      # y = x^2 / 5 as a row of spheres
    lines.append(f"goto {x * 2} {-40 + x * x / 5:.3f} 0\nsphere 0.6")
open("generated.logo", "w").write("\n".join(lines))
print("wrote generated.logo", len(lines), "lines")
