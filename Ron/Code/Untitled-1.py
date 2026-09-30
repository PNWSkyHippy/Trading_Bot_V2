temp_var = ""
name = ["mouse", "cat", "dog"]


def list_sort(list):
    for i in range(0, len(name)):
        if i < 2 and name[i] < name[i + 1]:
            temp_var = name[i]
            name[i] = name[i + 1]
            name[i + 1] = temp_var
    return list


print(f"I see {name}")
print(f"I see {list_sort(name)}")
