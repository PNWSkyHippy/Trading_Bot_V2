class Order:
    def __init__(self, item):
        self.item = item


orders = []
for _ in range(3):
    orders.append(Order("Apple"))
print(f"Length orders: {len(orders)}")
orders[0].item = "Oranges"
for o in orders:
    print(f"Order item: {o.item}")
