basic_list = ["131", "798", "465", "0"]


def str_sort(loc_str):
    """Sort a string alha-numrically"""
    loc_str_list = []
    # Build a list of the characters in string
    for i in range(len(loc_str)):
        loc_str_list.append(loc_str[i])
    # Then sort the list and then rejoin list into a string
    loc_str_list.sort()
    result = "".join(str(item) for item in loc_str_list)
    # Return the now sorted string
    return result


print(f"basic_list = {basic_list}")
basic_list.append("989")
print(f'basic list after append "989" = {basic_list}')

for i in range(len(basic_list)):
    print(f"basic_list[{i}] = {basic_list[i]}")
    basic_list[i] = str_sort(basic_list[i])
print(f"Each string in basic list sorted: {basic_list}")

for item in basic_list:
    print(f'Alternate way to iterate a list, using item in list "{item}"')

basic_list.sort()
print(f"basic_lists strings sorted = {basic_list}")

orders = [
    {
        "seller": "Amy",
        "category": "garden",
        "amount": 10,
    },
    {
        "seller": "Bob",
        "category": "books",
        "amount": 5,
    },
    {
        "seller": "Amy",
        "category": "garden",
        "amount": 8,
    },
    {
        "seller": "Bob",
        "category": "garden",
        "amount": 4,
    },
]
print(f"A Basic dicinary: {orders[0]}")
print(f"List of dictionarys named orders: {orders}")
my_dict = {}
dict_of_gardens = my_dict
print(f"for order in orders:\n")
for order in orders:
    print(f'\tcat = order["category"] returns {order["category"]}')
    categories = order["category"]
    if categories == "garden":
        my_seller = order["seller"]
        my_amont = order["amount"]
    print(
        f'To build a dictioary of lists with key "garden" and'
        f"values a list of each inividual seller and his/her total amount"
    )
    entry = f"{my_seller}: {my_amont}"
    dict_of_gardens.setdefault(categories, []).append(entry)

#        dict_of_gardens.setdefault(category, []).append(my_dict)
print(dict_of_gardens)
