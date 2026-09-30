class Team:
    members = 0

    def __init__(self, name):
        self.name = name
        Team.members = Team.members + 1


t1 = Team("A")
t2 = Team("B")
print(Team.members)
