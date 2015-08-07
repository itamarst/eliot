from sys import stdout
from eliot import start_action, start_task, to_file
to_file(stdout)


class Place(object):
    def __init__(self, name, contained=()):
        self.name = name
        self.contained = contained

    def visited(self, person):
        with start_action(action_type="place:visited",
                          person=person, place=self.name):
            for thing in self.contained:
                thing.visited(person)


def honeymoon(family, destination):
    with start_task(action_type="honeymoon", family=family):
        for person in family:
            destination.visited(person)


honeymoon(["Mrs. Casaubon", "Mr. Casaubon"],
          Place("Rome, Italy",
                [Place("Vatican Museum",
                       [Place("Statue #1"), Place("Statue #2")])]))
