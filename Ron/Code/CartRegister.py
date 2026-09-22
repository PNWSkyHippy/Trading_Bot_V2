cart = []
Q_Pressed = False


def add_item(local_cart, local_item):
    local_cart.append(local_item)
    return local_cart


def remove_item(local_cart, local_item):
    if local_item.strip() in local_cart:
        local_cart.remove(local_item)
        return local_cart, True
    else:
        return local_cart, False


def list_cart(local_cart):
    print("Cart List: ")
    for i in range(0, len(local_cart)):
        print(f"{local_cart[i]}")


while Q_Pressed == False:
    users_choice = input(
        "\n\n(A)dd Item\n"
        + "(R)emove Item\n"
        + "(S)how Cart\n"
        + "(Q)uit             : "
    )
    if isinstance(users_choice, str) and (len(users_choice) > 0):
        if users_choice[0].upper() == "Q":
            print(f"\nTotal Items in the Cart: {len(cart)}")
            Q_Pressed = True
        elif users_choice[0].upper() == "A":
            item = input("\nEnter the Item to Add: ")
            cart = add_item(cart, item)
        elif users_choice[0].upper() == "R":
            item = input("\nEnter the Item to Remove: ")
            cart, bool_flag = remove_item(cart, item)
            if bool_flag == False:
                print("\nIm sorry that item is not in the list")
        elif users_choice[0].upper() == "S":
            list_cart(cart)
        else:
            print("\nIm sorry that was an invalid entry please try again")
