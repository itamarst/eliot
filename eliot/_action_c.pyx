import cython
from pyrsistent import pvector


@cython.freelist(100)
cdef class TaskLevel(object):
    """
    The location of a message within the tree of actions of a task.

    @ivar level: A pvector of integers. Each item indicates a child
        relationship, and the value indicates message count. E.g. C{[2,
        3]} indicates this is the third message within an action which is
        the second item in the task.
    """
    cdef list _level

    def __cinit__(self, level):
        self._level = level

    cpdef list as_list(self):
        """Return the current level.

        @return: List of integers.
        """
        return self._level[:]

    # Backwards compatibility:
    @property
    def level(self):
        return pvector(self._level)

    def __lt__(self, other):
        return self._level < other._level

    def __le__(self, other):
        return self._level <= other._level

    def __gt__(self, other):
        return self._level > other._level

    def __ge__(self, other):
        return self._level >= other._level

    def __eq__(self, other):
        if other.__class__ != TaskLevel:
            return False
        return self._level == other._level

    def __ne__(self, other):
        if other.__class__ != TaskLevel:
            return True
        return self._level != other._level

    def __hash__(self):
        return hash(tuple(self._level))

    @staticmethod
    def fromString(string):
        """
        Convert a serialized Unicode string to a L{TaskLevel}.

        @param string: Output of L{TaskLevel.toString}.

        @return: L{TaskLevel} parsed from the string.
        """
        return TaskLevel(level=[int(i) for i in string.split("/") if i])

    cpdef str toString(self):
        """
        Convert to a Unicode string, for serialization purposes.

        @return: L{unicode} representation of the L{TaskLevel}.
        """
        return "/" + "/".join(map(unicode, self._level))

    cpdef TaskLevel next_sibling(self):
        """
        Return the next L{TaskLevel}, that is a task at the same level as this
        one, but one after.

        @return: L{TaskLevel} which follows this one.
        """
        new_level = self._level[:]
        new_level[-1] += 1
        return TaskLevel(level=new_level)

    cpdef TaskLevel child(self):
        """
        Return a child of this L{TaskLevel}.

        @return: L{TaskLevel} which is the first child of this one.
        """
        new_level = self._level[:]
        new_level.append(1)
        return TaskLevel(level=new_level)

    cpdef TaskLevel parent(self):
        """
        Return the parent of this L{TaskLevel}, or C{None} if it doesn't have
        one.

        @return: L{TaskLevel} which is the parent of this one.
        """
        if not self._level:
            return None
        return TaskLevel(level=self._level[:-1])

    cpdef is_sibling_of(self, task_level):
        """
        Is this task a sibling of C{task_level}?
        """
        return self.parent() == task_level.parent()

    # PEP 8 compatibility:
    from_string = fromString
    to_string = toString
