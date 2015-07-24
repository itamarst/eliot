from __future__ import unicode_literals
from sys import stdout

from eliot import Message, to_file
to_file(stdout)


class Person(object):
    def __init__(self, name):
        self.name = name


class Place(object):
    def __init__(self, name, contained=()):
        self.name = name
        self.contained = contained

    def visited(self, person):
        Message.log(message_type="place:visited",
                    person=person.name,
                    place=self.name)
        for thing in self.contained:
            thing.visited(person)


def honeymoon(family):
    Message.log(message_type="honeymoon",
                family=[person.name for person in family])
    rome = Place("Rome, Italy", [Place("Vatican Museum",
                                       [Place("Statue #1"),
                                        Place("Statue #2")])])
    for person in family:
        rome.visited(person)


if __name__ == '__main__':
    honeymoon([Person("Mrs. Casaubon"), Person("Mr. Casaubon")])
