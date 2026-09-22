print("list comprehensions")
print("squares = [n ** 2 for n in range(1, 6)]")
squares = [n**2 for n in range(1, 6)]
print(f"squares - {squares}")

print("\nexample 2")
print("evens = [n for n in range(20) if n % 2 == 0]")
evens = [n for n in range(20) if n % 2 == 0]
print(f"evens = {evens}")

print("\nexample 3")
print('upper_names = [name.upper() for name in ["ron", "ana"]]')
upper_names = [name.upper() for name in ["ron", "ana"]]
print(f"upper_names = {upper_names}\n")

print("\nset comprehensions")
print('words = ["cat", "dog", "cat", "bird"]')
print("lengths = {len(w) for w in words}")
words = ["cat", "dog", "cat", "bird"]
lengths = {len(w) for w in words}
print(f"lengths = {lengths}\n")

print("dict comprehension")
print('names = ["Ron", "Ana", "Sam"]')
print("name_lengths = {{name: len(name) for name in names}}")
names = ["Ron", "Ana", "Sam"]
name_lengths = {name: len(name) for name in names}
print(f"name_lengths = {name_lengths}")

print("\nexample 2")
print('prices = {"apple": 1.00, "milk": 3.50, "bread": 2.00}')
print(
    "on_sale = {{item: round(price * 0.8, 2) for item, price in prices.items() if price > 1.5}}"
)
prices = {
    "apple": 1.00,
    "milk": 3.50,
    "bread": 2.00,
}
on_sale = {item: round(price * 0.8, 2) for item, price in prices.items() if price > 1.5}
print(f"on_sale = {on_sale}\n")

print("\na generator expression")
print("squares_gen = (n ** 2 for n in range(1_000_000))")
squares_gen = (n**2 for n in range(1_000_000))
print(f"squares_gen = {squares_gen}")

print("\nexample 2:")
print("total = sum(n ** 2 for n in range(10))")
total = sum(n**2 for n in range(10))
print(f"total = {total}")
print("for val in squares_gen:")
print("\tval")
print("\tbreak")
i = 0
for val in squares_gen:
    print(val)
    i += 1
    if i == 4:
        break
print(".....")

print("\nconditional expression")
print("age = 20")
print('status = "adult" if age >= 18 else "minor"')
age = 20
status = "adult" if age >= 18 else "minor"
print(f"status = {status}")

print('\nexample 2" inside a list comprehension')
print('labels = ["even" if n % 2 == 0 else "odd" for n in range(5)]')
labels = ["even" if n % 2 == 0 else "odd" for n in range(5)]
print(f"labels = {labels}")

print("\nexample 3: inside an f-string")
print("print(f\"You are {'eligible' if age >= 18 else 'not eligible'} to vote\")")
print(f"You are {'eligible' if age >= 18 else 'not eligible'} to vote")

print("\the walrus operator")
print("without walrus")
print('line = input("Enter text (blank to quit):')
print('while line != "":')
print('\tprint(f"You typed: {line}")')
print('\tline = input("Enter text (blank to quit): ")')
line = input("Enter text (blank to quit): ")
while line != "":
    print(f"You typed: {line}")
    line = input("Enter text (blank to quit): ")

print("\nwith walrus")
print('while (line := input("Enter text (blank to quit): ")) != "":')
print('\tprint(f"You typed: {line}")')
while (line := input("Enter text (blank to quit): ")) != "":
    print(f"You typed: {line}")

print("\nexample 2: avoiding a duplicate call in an if")
print("data = [1, 2, 3, 4, 5]")
print("if (n := len(data)) > 3:")
print('\tprint(f"List is long: {n} items")')
data = [1, 2, 3, 4, 5]
if (n := len(data)) > 3:
    print(f"List is long: {n} items")

print("\ninside a comprehension — compute once, filter and reuse the same value")
print("results = [y for x in range(10) if (y := x ** 2) > 20]")
results = [y for x in range(10) if (y := x**2) > 20]
print(f"results = {results}")
