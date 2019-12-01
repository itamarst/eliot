from sys import stdout
from eliot import start_action, to_file
to_file(stdout)


class Place(object):
    def __init__(self, name, contained=()):
        self.name = name
        self.contained = contained

    def visited(self, people):
        # No need to repetitively log people, since caller will:
        with start_action(action_type="visited", place=self.name):
            for thing in self.contained:
                thing.visited(people)


def honeymoon(family, destination):
    with start_action(action_type="honeymoon", people=family):
        destination.visited(family)


honeymoon(["Mrs. Casaubon", "Mr. Casaubon"],
          Place("Rome, Italy",
                [Place("Vatican Museum",
                       [Place("Statue #1"), Place("Statue #2")])]))
