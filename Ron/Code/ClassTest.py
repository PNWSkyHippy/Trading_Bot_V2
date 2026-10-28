"""Provide list-backed sequence classes (point and CList) with deque-style helpers."""

from collections.abc import MutableSequence
from typing import Any

class point(MutableSequence):
    """Store point coordinates in a mutable sequence backed by a list."""

    def __init__(self, arg_list=None):
        """Initialize the sequence.

        Args:
            arg_list (Iterable | None): Initial items. Defaults to empty.
        """
        coords = []
        
        self.coords: Any = list(arg_list) if arg_list is not None else []

    def __str__(self):
        """Return the container type name and its items.

        Returns:
            str: A readable description of the contents.
        """
        return f"list type: {self.coords}"
    
    def __repr__(self):
        """Return an unambiguous representation.

        Returns:
            str: A string that shows the class name and items.
        """
        return f"point({self.coords!r})"
    
    def show(self):
        """Return the stored list.

        Returns:
            list: The underlying list, not a copy.
        """
        return self.coords

    def count(self,item):
        """Count occurrences of an item.

        Args:
            item (object): The value to count.

        Returns:
            int: How many times ``item`` appears.
        """
        return (self.coords.count(item))

    def reverse(self):
        """Reverse the items in place.

        Returns:
            None: Always, as with ``list.reverse``.
        """
        return (self.coords.reverse())

    def copy(self):
        """Return a shallow copy of the items.

        Returns:
            list: A new list with the same items.
        """
        return (self.coords.copy())
        
    def sorted(self):
        """Return the items sorted, leaving the original unchanged.

        Returns:
            list: A new sorted list.
        """
        return sorted(self.coords)

    def sort(self, key=None, reverse=False):
        """Sort the items in place.

        Args:
            key (Callable | None): Accepted but ignored.
            reverse (bool): Accepted but ignored.

        Returns:
            list: The sorted underlying list.
        """
        self.coords.sort()
        return self.coords

    def insert(self, idx, item):
        """Insert an item before an index.

        Args:
            idx (int): Position to insert before.
            item (object): The value to insert.

        Returns:
            int: Always 1.
        """
        self.coords.insert(idx, item)
        return 1
    
    def append(self, item):
        """Add an item to the end.

        Args:
            item (object): The value to add.

        Returns:
            int: Always 1.
        """
        self.coords.append(item)
        return 1

    def clear(self):
        """Remove all items.

        Returns:
            int: Always 1.
        """
        self.coords.clear()
        return 1

    def appendleft(self, item):
        """Add an item to the front.

        Args:
            item (object): The value to add.

        Returns:
            int: Always 1.
        """
        self.coords.insert(0,item)
        return 1

    def popleft(self):
        """Remove and return the first item.

        Returns:
            object: The first item, or 0 if the sequence is empty.
        """
        try:
            return self.coords.pop(0)
        except IndexError:
            return 0

    def pop(self, idx=-1):
        """Remove and return an item.

        Args:
            idx (int): Index to remove. Defaults to the last item.

        Returns:
            object: The removed item, or 0 if the index is out of range.
        """
        try:
            return self.coords.pop(idx)
        except IndexError:
            return 0
        
    def remove(self, item):
        """Remove the first occurrence of an item.

        Args:
            item (object): The value to remove.

        Returns:
            int: 1 if the item was removed, 0 if it was not found.
        """
        if item in self.coords:
            self.coords.remove(item)
            return 1
        else: return 0
    
    def swap(self, itm1, itm2):
        """Swap two items.

        Args:
            itm1 (int): Index of the first item.
            itm2 (int): Index of the second item.

        Returns:
            list: The underlying list after the swap.

        Raises:
            IndexError: If either index is out of range.
        """
        if not (0 <= itm1 < len(self.coords) and 0 <= itm2 < len(self.coords)):
            raise IndexError("swap indices out of range")
        self.coords[itm1], self.coords[itm2] = self.coords[itm2], self.coords[itm1]
        return self.coords

    def __len__(self):
        """Return the number of items.

        Returns:
            int: The item count.
        """
        return len(self.coords)

    def __iter__(self):
        """Iterate over the items.

        Returns:
            Iterator: An iterator over the underlying list.
        """
        return iter(self.coords)

    def __getitem__(self, key):
        """Return the item or slice at a key.

        Args:
            key (int | slice): Index or slice to read.

        Returns:
            object: The selected item or items.
        """
        return self.coords[key]

    def __setitem__(self, key, value):
        """Replace the item at a key.

        Args:
            key (int | slice): Index or slice to replace.
            value (object): The new value.
        """
        self.coords[key] = value

    def __delitem__(self, key):
        """Delete the item at a key.

        Args:
            key (int | slice): Index or slice to delete.
        """
        del self.coords[key]

    def __eq__(self, obj):
        """Compare with another instance of the same class.

        Args:
            obj (object): The object to compare with.

        Returns:
            bool: True if the items are equal, or ``NotImplemented`` for
            other types.
        """
        if not isinstance(obj, point):
            return NotImplemented
        return self.coords == obj.coords
    def set_loc(self, newx, newy, newz):
        """Set all three coordinates.

        Args:
            newx (float): The new x value.
            newy (float): The new y value.
            newz (float): The new z value.
        """
        self.coords[0] = newx
        self.coords[1] = newy
        self.coords[2] = newz
        
    def set_x(self, newx):
        """Set the x coordinate.

        Args:
            newx (float): The new x value.
        """
        self.coords[0] = newx
                    
    def set_y(self, newy):
        """Set the y coordinate.

        Args:
            newy (float): The new y value.
        """
        self.coords[1] = newy

    def set_z(self, newz):
        """Set the z coordinate.

        Args:
            newz (float): The new z value.
        """
        self.coords[2] = newz

class CList(MutableSequence):
    """Wrap a list as a mutable sequence with deque-style helpers.

    Attributes:
        ctype (type): The backing container type, used in ``__str__``.
        data (list): The stored items.
    """
    ctype = list

    def __init__(self, arg_list=None):
        """Initialize the sequence.

        Args:
            arg_list (Iterable | None): Initial items. Defaults to empty.
        """
        self.data: Any = list(arg_list) if arg_list is not None else []

    def __str__(self):
        """Return the container type name and its items.

        Returns:
            str: A readable description of the contents.
        """
        return f"{self.ctype.__name__} type: {self.data}"

    def __repr__(self):
        """Return an unambiguous representation.

        Returns:
            str: A string that shows the class name and items.
        """
        return f"CList({self.data!r})"

    def show(self):
        """Return the stored list.

        Returns:
            list: The underlying list, not a copy.
        """
        return self.data

    def count(self,item):
        """Count occurrences of an item.

        Args:
            item (object): The value to count.

        Returns:
            int: How many times ``item`` appears.
        """
        return (self.data.count(item))

    def reverse(self):
        """Reverse the items in place.

        Returns:
            None: Always, as with ``list.reverse``.
        """
        return (self.data.reverse())

    def copy(self):
        """Return a shallow copy of the items.

        Returns:
            list: A new list with the same items.
        """
        return (self.data.copy())
        
    def sorted(self):
        """Return the items sorted, leaving the original unchanged.

        Returns:
            list: A new sorted list.
        """
        return sorted(self.data)

    def sort(self, key=None, reverse=False):
        """Sort the items in place.

        Args:
            key (Callable | None): Accepted but ignored.
            reverse (bool): Accepted but ignored.

        Returns:
            list: The sorted underlying list.
        """
        self.data.sort()
        return self.data

    def insert(self, idx, item):
        """Insert an item before an index.

        Args:
            idx (int): Position to insert before.
            item (object): The value to insert.

        Returns:
            int: Always 1.
        """
        self.data.insert(idx, item)
        return 1
    
    def append(self, item):
        """Add an item to the end.

        Args:
            item (object): The value to add.

        Returns:
            int: Always 1.
        """
        self.data.append(item)
        return 1

    def clear(self):
        """Remove all items.

        Returns:
            int: Always 1.
        """
        self.data.clear()
        return 1

    def appendleft(self, item):
        """Add an item to the front.

        Args:
            item (object): The value to add.

        Returns:
            int: Always 1.
        """
        self.data.insert(0,item)
        return 1

    def popleft(self):
        """Remove and return the first item.

        Returns:
            object: The first item, or 0 if the sequence is empty.
        """
        try:
            return self.data.pop(0)
        except IndexError:
            return 0

    def pop(self, idx=-1):
        """Remove and return an item.

        Args:
            idx (int): Index to remove. Defaults to the last item.

        Returns:
            object: The removed item, or 0 if the index is out of range.
        """
        try:
            return self.data.pop(idx)
        except IndexError:
            return 0
        
    def remove(self, item):
        """Remove the first occurrence of an item.

        Args:
            item (object): The value to remove.

        Returns:
            int: 1 if the item was removed, 0 if it was not found.
        """
        if item in self.data:
            self.data.remove(item)
            return 1
        else: return 0
    
    def swap(self, itm1, itm2):
        """Swap two items.

        Args:
            itm1 (int): Index of the first item.
            itm2 (int): Index of the second item.

        Returns:
            list: The underlying list after the swap.

        Raises:
            IndexError: If either index is out of range.
        """
        if not (0 <= itm1 < len(self.data) and 0 <= itm2 < len(self.data)):
            raise IndexError("swap indices out of range")
        self.data[itm1], self.data[itm2] = self.data[itm2], self.data[itm1]
        return self.data

    def __len__(self):
        """Return the number of items.

        Returns:
            int: The item count.
        """
        return len(self.data)

    def __iter__(self):
        """Iterate over the items.

        Returns:
            Iterator: An iterator over the underlying list.
        """
        return iter(self.data)

    def __getitem__(self, key):
        """Return the item or slice at a key.

        Args:
            key (int | slice): Index or slice to read.

        Returns:
            object: The selected item or items.
        """
        return self.data[key]

    def __setitem__(self, key, value):
        """Replace the item at a key.

        Args:
            key (int | slice): Index or slice to replace.
            value (object): The new value.
        """
        self.data[key] = value

    def __delitem__(self, key):
        """Delete the item at a key.

        Args:
            key (int | slice): Index or slice to delete.
        """
        del self.data[key]

    def __eq__(self, obj):
        """Compare with another instance of the same class.

        Args:
            obj (object): The object to compare with.

        Returns:
            bool: True if the items are equal, or ``NotImplemented`` for
            other types.
        """
        if not isinstance(obj, CList):
            return NotImplemented
        return self.data == obj.data

adot = point([5.0, 3.0, 6.0])

myList = CList()
myList.data = [5, 7, 3, 6, 1, 4, 2]
print(type(myList))
print(myList.show())
my_value = myList.pop(6)
print(f'Popped {my_value} , myList now holds {myList.show()}')
sorted_list = myList.sorted()
print(f'sorted_list = {sorted_list}\nmyList = {myList.show()}')
myList.insert(2, my_value)
print(f'After insert of {my_value} at position 2: myList = {myList.show()}')
myList.remove(1)
print(f' myList after remove(1): {myList.show()}')
myList.appendleft(27)
popped = myList.popleft()
print(f'appendedleft(27), ran popleft, returned {popped}')
myList.appendleft(26)
print(f'myList after appendleft(26): {myList.show()}')
print(f'myList after swapping items 2 and 3: {myList.swap(2, 3)}')
print(f'myList itself sorted in place: {myList.sort()}')
myList[2] = 69
print(f'myList after myList[2] = 69: {myList.show()}')
value = myList[3]
print(f'myList[3] == {value}')
print(f'for x in iter(myList)')
for x in iter(myList):
    print(f'x == {x}')
print(f'len(myList) is: {len(myList)}')



