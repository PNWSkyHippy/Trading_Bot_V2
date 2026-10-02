class Team:
    members = 0

    def __init__(self, name):
        self.name = name
        Team.members = Team.members + 1


t1 = Team("A")
t2 = Team("B")
print(Team.members)

my_list = [
    ["x", "y", "z"],
    ["A", "b", "c"],
    ["1", "2", "3"],
    ["d", "e", "f"],
]
prices = {
    "apple": 1.00,
    "milk": 3.50,
    "bread": 2.00,
}
on_sale = {item: round(price * 0.8, 2) for item, price in prices.items() if price > 1.5}
print(f"on_sale = {on_sale}\n")
