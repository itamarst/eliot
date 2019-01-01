from os import getpid

from dask.bag import from_sequence
import dask.config
from dask.distributed import Client
from eliot import log_call, to_file
from eliot.dask import compute_with_trace


@log_call
def multiply(x, y=7):
    return x * y

@log_call
def add(x, y):
    return x + y

@log_call
def main_computation():
    bag = from_sequence([1, 2, 3])
    bag = bag.map(multiply).map(multiply).fold(add)
    return compute_with_trace(bag)  # instead of dask.compute(bag)

def _start_logging():
    to_file(open("{}.log".format(getpid()), "a"))

def main():
    # Setup logging on the main process:
    _start_logging()

    # Setup Distributed scheduler, on local machine:
    client = Client(n_workers=2, threads_per_worker=1)

    # Setup Eliot logging on each worker process:
    client.run(_start_logging)

    # Run the Dask computation:
    main_computation()


if __name__ == '__main__':
    import dask_eliot
    dask_eliot.main()
