var_sixty = 0.6
wweeks_review_score = [0, 0, 0]
weeks_discuss = [0, 0, 0, 0]

for i in range(0, len(wweeks_review_score)):
    wweeks_review_score[i] = float(
        input(
            f"Enter week {i + 1}'s "
            + "review score: "
        )
    )
for i in range(0, len(weeks_discuss)):
    weeks_discuss[i] = float(
        input(
            f"Enter week {i + 1}'s discussion score: "
        )
    )
final_exam_score = float(
    input("Enter the score on your final exam: ")
)
final_score = (
    (var_sixty * final_exam_score)
    + sum(wweeks_review_score)
    + sum(weeks_discuss)
)
print(f"Your final score is: {final_score}")
