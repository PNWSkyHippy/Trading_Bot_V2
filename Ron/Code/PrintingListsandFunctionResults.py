my_list = [2, 4, 5, 7, 9, 15, 17]


def average(list):
    sum = 0
    for i in list:
        sum += i
    return sum / len(list)


print(
    f"The average of {my_list} is {average(my_list)}"
)
