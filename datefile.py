from datetime import datetime
end = str(datetime.now())
with open("notes.txt","a") as file:
    file.write(f"{datetime.now()}\n")

with open("notes.txt","r") as file2:
    for line in file2:
        print(line, end= "")