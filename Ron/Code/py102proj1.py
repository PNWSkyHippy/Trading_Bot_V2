my_array = [1,2,3,4,5,6]

def safe_get(arr, index):
    res = arr[index] if 0 <= index < len(arr) else "Out of range"
    return res

def main():
    print(f"Result of safe_get(2): {safe_get(my_array, 2)}")
    print(f"Result of safe_get(-2): {safe_get(my_array, -2)}")
    print(f"Result of safe_get(6): {safe_get(my_array, 6)}")
    print(f"Result of safe_get(5): {safe_get(my_array, 5)}")

if __name__ == "__main__":
    main()
     