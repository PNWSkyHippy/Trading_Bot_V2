numbers = [1, 2, 3, 4]


def square(n):
    value = n * n
    return value
    # TODO: finish this helper


def main():
    squared = []
    for num in numbers:
        squared.append(square(num))
        # TODO: use square() here and append to squared

    print(squared)


main()
