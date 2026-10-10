
from local_functions import run_sorting_algorithm, Timed
from random import randint
from timeit import repeat

@Timed
def bubble_sort(array):
    n = len(array)

    for i in range(n):
        # Create a flag that will allow the function to
        # terminate early if there's nothing left to sort
        already_sorted = True

        # Start looking at each item of the list one by one,
        # comparing it with its adjacent value. With each
        # iteration, the portion of the array that you look at
        # shrinks because the remaining items have already been
        # sorted.
        for j in range(n - i - 1):
            if array[j] > array[j + 1]:
                # If the item you're looking at is greater than its
                # adjacent value, then swap them
                array[j], array[j + 1] = array[j + 1], array[j]

                # Since you had to swap two elements,
                # set the `already_sorted` flag to `False` so the
                # algorithm doesn't finish prematurely
                already_sorted = False

        # If there were no swaps during the last iteration,
        # the array is already sorted, and you can terminate
        if already_sorted:
            break

    return array

@Timed
def insertion_sort(array):
    # Loop from the second element of the array until
    # the last element
    for i in range(1, len(array)):
        # This is the element we want to position in its
        # correct place
        key_item = array[i]

        # Initialize the variable that will be used to
        # find the correct position of the element referenced
        # by `key_item`
        j = i - 1

        # Run through the list of items (the left
        # portion of the array) and find the correct position
        # of the element referenced by `key_item`. Do this only
        # if `key_item` is smaller than its adjacent values.
        while j >= 0 and array[j] > key_item:
            # Shift the value one position to the left
            # and reposition j to point to the next element
            # (from right to left)
            array[j + 1] = array[j]
            j -= 1

        # When you finish shifting the elements, you can position
        # `key_item` in its correct location
        array[j + 1] = key_item

    return array

@Timed
def merge(left, right):
    # If the first array is empty, then nothing needs
    # to be merged, and you can return the second array as the result
    if len(left) == 0:
        return right

    # If the second array is empty, then nothing needs
    # to be merged, and you can return the first array as the result
    if len(right) == 0:
        return left

    result = []
    index_left = index_right = 0

    # Now go through both arrays until all the elements
    # make it into the resultant array
    while len(result) < len(left) + len(right):
        # The elements need to be sorted to add them to the
        # resultant array, so you need to decide whether to get
        # the next element from the first or the second array
        if left[index_left] <= right[index_right]:
            result.append(left[index_left])
            index_left += 1
        else:
            result.append(right[index_right])
            index_right += 1

        # If you reach the end of either array, then you can
        # add the remaining elements from the other array to
        # the result and break the loop
        if index_right == len(right):
            result += left[index_left:]
            break

        if index_left == len(left):
            result += right[index_right:]
            break

    return result

@Timed
def merge_sort(array):
    # If the input array contains fewer than two elements,
    # then return it as the result of the function
    if len(array) < 2:
        return array

    midpoint = len(array) // 2

    # Sort the array by recursively splitting the input
    # into two equal halves, sorting each half and merging them
    # together into the final result
    return merge(
        left=merge_sort(array[:midpoint]),
        right=merge_sort(array[midpoint:]))
    
    from random import randint

@Timed
def python_sort(array):
    array.sort()

@Timed
def python_sorted(array):
    new_array  =  sorted(array)
    return new_array

@Timed
def quicksort(array):
    # If the input array contains fewer than two elements,
    # then return it as the result of the function
    if len(array) < 2:
        return array

    low, same, high = [], [], []

    # Select your `pivot` element randomly
    pivot = array[randint(0, len(array) - 1)]

    for item in array:
        # Elements that are smaller than the `pivot` go to
        # the `low` list. Elements that are larger than
        # `pivot` go to the `high` list. Elements that are
        # equal to `pivot` go to the `same` list.
        if item < pivot:
            low.append(item)
        elif item == pivot:
            same.append(item)
        elif item > pivot:
            high.append(item)

    # The final result combines the sorted `low` list
    # with the `same` list and the sorted `high` list
    return quicksort(low) + same + quicksort(high)

@Timed
def timinsertion_sort(array, left=0, right=None):
    if right is None:
        right = len(array) - 1

    # Loop from the element indicated by
    # `left` until the element indicated by `right`
    for i in range(left + 1, right + 1):
        # This is the element we want to position in its
        # correct place
        key_item = array[i]

        # Initialize the variable that will be used to
        # find the correct position of the element referenced
        # by `key_item`
        j = i - 1

        # Run through the list of items (the left
        # portion of the array) and find the correct position
        # of the element referenced by `key_item`. Do this only
        # if the `key_item` is smaller than its adjacent values.
        while j >= left and array[j] > key_item:
            # Shift the value one position to the left
            # and reposition `j` to point to the next element
            # (from right to left)
            array[j + 1] = array[j]
            j -= 1

        # When you finish shifting the elements, position
        # the `key_item` in its correct location
        array[j + 1] = key_item

    return array

@Timed
def timsort(array):
    min_run = 32
    n = len(array)

    # Start by slicing and sorting small portions of the
    # input array. The size of these slices is defined by
    # your `min_run` size.
    for i in range(0, n, min_run):
        timinsertion_sort(array, i, min((i + min_run - 1), n - 1))

    # Now you can start merging the sorted slices.
    # Start from `min_run`, doubling the size on
    # each iteration until you surpass the length of
    # the array.
    size = min_run
    while size < n:
        # Determine the arrays that will
        # be merged together
        for start in range(0, n, size * 2):
            # Compute the `midpoint` (where the first array ends
            # and the second starts) and the `endpoint` (where
            # the second array ends)
            midpoint = start + size - 1
            end = min((start + size * 2 - 1), (n-1))

            # Merge the two subarrays.
            # The `left` array should go from `start` to
            # `midpoint + 1`, while the `right` array should
            # go from `midpoint + 1` to `end + 1`.
            merged_array = merge(
                left=array[start:midpoint + 1],
                right=array[midpoint + 1:end + 1])

            # Finally, put the merged array back into
            # your array
            array[start:start + len(merged_array)] = merged_array

        # Each iteration should double the size of your arrays
        size *= 2

    return array
ARRAY_LENGTH = 200000
if __name__ == "__main__":
    # Generate an array of `ARRAY_LENGTH` items consisting
    # of random integer values between 0 and 999
    array = [randint(0, 1000) for i in range(ARRAY_LENGTH)]

    # Call the function using the name of the sorting 
    # and the array you just created
    run_sorting_algorithm(algorithm="python_sort", array=array)
    print(f"python_sort: {python_sort.elapsed}")
    sorted = run_sorting_algorithm(algorithm="python_sorted", array=array)
    print(f"python_sorted: {python_sorted.elapsed}")
    run_sorting_algorithm(algorithm="merge_sort", array=array)
    print(f"mwerge_sort: {merge_sort.elapsed}")
    run_sorting_algorithm(algorithm="quicksort", array=array)
    print(f"quicksort: {quicksort.elapsed}")
    run_sorting_algorithm(algorithm="timsort", array=array)
    print(f"timsort: {timsort.elapsed}")
    run_sorting_algorithm(algorithm="insertion_sort", array=array)
    print(f"timsort: {insertion_sort.elapsed}")
    run_sorting_algorithm(algorithm="bubble_sort", array=array)
    print(f"timsort: {bubble_sort.elapsed}")