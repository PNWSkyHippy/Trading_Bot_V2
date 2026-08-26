matrix = [[2, 4, 6], [1, 3, 5], [10, 20, 30]]

matrix[1][2] = matrix[0][1] + matrix[2][0]
print(matrix[1][2])
scores = [15]
for score in scores:
    if score < 60:
        scores.remove(score)
print(scores)
