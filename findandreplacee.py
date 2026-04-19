import sys

# Ensure enough arguments are provided
if len(sys.argv) < 4:
    print("Usage: python script.py <original text> <replacement text> <file>")
    sys.exit(1)

# Reference them with variables
first_var = sys.argv[1]
second_var = sys.argv[2]
third_var = sys.argv[3]
(Get-Content third_var) -replace first_var, second_var | Set-Content third_var