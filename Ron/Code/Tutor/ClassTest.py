from collections.abc import MutableSequence
from typing import Any


class CList(MutableSequence):
    ctype = list

    def __init__(self, arg_list=None):
        self.data: Any = list(arg_list) if arg_list is not None else []

    def __str__(self):
        return f"{self.ctype.__name__} type: {self.data}"

    def __repr__(self):
        return f"CList({self.data!r})"

    def show(self):
        return self.data

    def count(self,item):
        return (self.data.count(item))

    def reverse(self):
        return (self.data.reverse())

    def copy(self):
        return (self.data.copy())
        
    def sorted(self):
        return sorted(self.data)

    def sort(self, key=None, reverse=False):
        self.data.sort(key,reverse)
        return self.data

    def insert(self, idx, item):
        self.data.insert(idx, item)
        return 1
    
    def append(self, item):
        self.data.append(item)
        return 1

    def clear(self):
        self.data.clear()
        return 1

    def appendleft(self, item):
        self.data.insert(0,item)
        return 1

    def popleft(self):
        try:
            return self.data.pop(0)
        except IndexError:
            return 0

    def pop(self, idx=-1):
        try:
            return self.data.pop(idx)
        except IndexError:
            return 0
        
    def remove(self, item):
        if item in self.data:
            self.data.remove(item)
            return 1
        else: return 0
    
    def swap(self, itm1, itm2):
        if not (0 <= itm1 < len(self.data) and 0 <= itm2 < len(self.data)):
            raise IndexError("swap indices out of range")
        self.data[itm1], self.data[itm2] = self.data[itm2], self.data[itm1]
        return self.data

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __eq__(self, obj):
        if not isinstance(obj, CList):
            return NotImplemented
        return self.data == obj.data


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



