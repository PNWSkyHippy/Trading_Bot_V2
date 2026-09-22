nums = [10, 20, 30]
nums.pop(0)
nums.append(40)
nums[0] = nums[0] + nums[-1]
print(nums)

vals = [5, 10, 15]
vals.append(20)
vals.pop(1)
print(vals[0])

stack = ["open file", "edit", "save"]
stack.pop()
stack.pop()
stack.append("print")
print(stack)


em_stack = []
em_stack.append(1)
em_stack.append(2)
em_stack.append(3)
em_stack.pop()
em_stack.pop()
em_stack.append(4)
print(em_stack)

number = [1, 2, 4, 5, 6]
for x in number:
    if x % 2 == 0:
        number.remove(x)
print(number)
