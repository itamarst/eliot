from __future__ import unicode_literals
from sys import stdout

from eliot import Message, start_action, start_task, to_file
to_file(stdout)


class Person(object):
    def __init__(self, name):
        self.name = name
        self.seen = set()

    def look(self, thing):
        Message.log(message_type="person:look",
                    person=self.name,
                    at=thing.name)
        self.seen.add(thing)


class Thing(object):
    def __init__(self, name):
        self.name = name


class Place(object):
    def __init__(self, name, contained=()):
        self.name = name
        self.contained = contained

    def travel(self, person):
        with start_action(action_type="place:travel",
                          person=person.name,
                          place=self.name):
            for thing in self.contained:
                if isinstance(thing, Place):
                    thing.travel(person)
                else:
                    person.look(thing)


def honeymoon(family):
    with start_task(action_type="honeymoon",
                    family=[person.name for person in family]):
        rome = Place("Rome, Italy", [Place("Vatican Museum",
                                           [Thing("Statue #1"),
                                            Thing("Statue #2")])])
        for person in family:
            rome.travel(person)


if __name__ == '__main__':
    honeymoon([Person("Mrs. Casaubon"), Person("Mr. Casaubon")])
