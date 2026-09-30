batch = [40, 26, 39, 30, 25, 21]
cutoff = 22
for item in batch:
    print(f"{item} is O.K")
    assert item >= cutoff, "Batch is Rejected"
