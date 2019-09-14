"""Support for Eliot tracing with Dask computations."""

from pyrsistent import PClass, field

from dask import compute, optimize
from dask.core import toposort, get_dependencies
from . import start_action, current_action, Action, Message


class _RunWithEliotContext(PClass):
    """
    Run a callable within an Eliot context.

    @ivar task_id: The serialized Eliot task ID.
    @ivar func: The function that Dask wants to run.
    @ivar key: The key in the Dask graph.
    @ivar dependencies: The keys in the Dask graph this depends on.
    """

    task_id = field(type=str)
    func = field()  # callable
    key = field(type=str)
    dependencies = field()

    # Pretend to be underlying callable for purposes of equality; necessary for
    # optimizer to be happy:

    def __eq__(self, other):
        return self.func == other

    def __ne__(self, other):
        return self.func != other

    def __hash__(self):
        return hash(self.func)

    def __call__(self, *args, **kwargs):
        with Action.continue_task(task_id=self.task_id):
            Message.log(
                message_type="dask:task", key=self.key, dependencies=self.dependencies
            )
            return self.func(*args, **kwargs)


def compute_with_trace(*args):
    """Do Dask compute(), but with added Eliot tracing.

    Dask is a graph of tasks, but Eliot logs trees.  So we need to emulate a
    graph using a tree.  We do this by making Eliot action for each task, but
    having it list the tasks it depends on.

    We use the following algorithm:

        1. Create a top-level action.

        2. For each entry in the dask graph, create a child with
           serialize_task_id.  Do this in likely order of execution, so that
           if B depends on A the task level of B is higher than the task Ievel
           of A.

        3. Replace each function with a wrapper that uses the corresponding
           task ID (with Action.continue_task), and while it's at it also
           records which other things this function depends on.

    Known issues:

        1. Retries will confuse Eliot.  Probably need different
           distributed-tree mechanism within Eliot to solve that.
    """
    # 1. Create top-level Eliot Action:
    with start_action(action_type="dask:compute"):
        # In order to reduce logging verbosity, add logging to the already
        # optimized graph:
        optimized = optimize(*args, optimizations=[_add_logging])
        return compute(*optimized, optimize_graph=False)


def _add_logging(dsk, ignore=None):
    """
    Add logging to a Dask graph.

    @param dsk: The Dask graph.

    @return: New Dask graph.
    """
    ctx = current_action()
    result = {}

    # Use topological sort to ensure Eliot actions are in logical order of
    # execution in Dask:
    keys = toposort(dsk)

    # Give each key a string name. Some keys are just aliases to other
    # keys, so make sure we have underlying key available. Later on might
    # want to shorten them as well.
    def simplify(k):
        if isinstance(k, str):
            return k
        return "-".join(str(o) for o in k)

    key_names = {}
    for key in keys:
        value = dsk[key]
        if not callable(value) and value in keys:
            # It's an alias for another key:
            key_names[key] = key_names[value]
        else:
            key_names[key] = simplify(key)

    # 2. Create Eliot child Actions for each key, in topological order:
    key_to_action_id = {key: str(ctx.serialize_task_id(), "utf-8") for key in keys}

    # 3. Replace function with wrapper that logs appropriate Action:
    for key in keys:
        func = dsk[key][0]
        args = dsk[key][1:]
        if not callable(func):
            # This key is just an alias for another key, no need to add
            # logging:
            result[key] = dsk[key]
            continue
        wrapped_func = _RunWithEliotContext(
            task_id=key_to_action_id[key],
            func=func,
            key=key_names[key],
            dependencies=[key_names[k] for k in get_dependencies(dsk, key)],
        )
        result[key] = (wrapped_func,) + tuple(args)

    assert set(result.keys()) == set(dsk.keys())
    return result


__all__ = ["compute_with_trace"]
