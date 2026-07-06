def safe_int():
    try:
        value = int(input("Enter a number: "))
    except ValueError:
        print("That wasn’t a valid number!")
    else:
        print("You entered:", value)
    finally:
        print("Done processing input.")


safe_int()
