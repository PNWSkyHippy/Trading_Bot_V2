item_count = 0
cart_items = []
total_items = 0
done = False
while not done:
    str_buffer = input("Please enter an iem name and its price: (just hit enter when done):")
    item, price = str_buffer.split() if len(str_buffer) > 0 else (None, None)
    price = float(price) if price else None
    if not item and not price:
        done = True
    elif item and not price:
        print("Please enter an item and a price")
    else:
        cart_items.append((item, price))
        total_items += 1  
if len(cart_items) < 1:
    print("cart is empty")
else:
    for items in cart_items:
        if item_count == 0:
            print(f'first item is:{items[0]}')
        item_count += 1
print(f'Item {item_count}')
    
    