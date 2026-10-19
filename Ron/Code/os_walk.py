import os

for root, dirs, files in os.walk('.'):
    print("Current directory:", root)
    print("Subdirectories:", dirs)
    print("Files:", files)
    print('----------------')