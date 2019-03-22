Scientific Computing with Eliot
===============================

When it takes hours or days to run your computation, it can take a long time before you notice something has gone wrong, so your feedback cycle for fixes can be very slow.
If you want to solve problems quickly—whether it's inconsistent results, crashes, or slowness—you need to understand what was going on in your process as it was running: you need logging.

Eliot is an ideal logging library for these cases:

* It provides structured logging, instead of prose, so you can see inputs, outputs, and intermediate results of your calculations.
* It gives you a trace of what happened, including causality: instead of just knowing that ``f()`` was called, you can distinguish between calls to ``f()`` from different code paths.
* It supports scientific libraries: NumPy and Dask.
  By default, Eliot will automatically serialize NumPy integers, floats, arrays, and bools to JSON (see :ref:`custom_json` for details).


.. _dask_usage:

Using Dask
----------

If you're using the `Dask <https://dask.pydata.org>`_ distributed computing framework, you can automatically use Eliot to trace computations across multiple processes or even machines.
This is mostly useful for Dask's Bag and Delayed support, but can also be used with arrays and dataframes.

In order to do this you will need to:

* Ensure all worker processes write the Eliot logs to disk (if you're using the ``multiprocessing`` or ``distributed`` backends).
* If you're using multiple worker machines, aggregate all log files into a single place, so you can more easily analyze them with e.g. `eliot-tree <https://github.com/jonathanj/eliottree>`_.
* Replace ``dask.compute()`` with ``eliot.dask.compute_with_trace()``.

In the following example, you can see how this works for a Dask run using ``distributed``, the recommended Dask scheduler.
We'll be using multiple worker processes, but only use a single machine:

.. literalinclude:: ../../examples/dask_eliot.py

In the output you can see how the various Dask tasks depend on each other, and the full trace of the computation:

.. code-block:: shell-session

   $ python examples/dask_eliot.py 
   Result: 42
   $ ls *.log
   7254.log  7269.log  7271.log  7273.log
   $ eliot-tree *.log
   ca126b8a-c611-447e-aaa7-f61701e2a371
   └── main_computation/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.047s
       ├── dask:compute/2/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.029s
       │   ├── eliot:remote_task/2/8/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.001s
       │   │   ├── dask:task/2/8/2 2019-01-01 17:27:13
       │   │   │   ├── dependencies: 
       │   │   │   │   └── 0: map-multiply-75feec3a197bf253863e330f3483d3ac-0
       │   │   │   └── key: reduce-part-71950de8264334e8cea3cc79d1c2e639-0
       │   │   ├── multiply/2/8/3/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.000s
       │   │   │   ├── x: 1
       │   │   │   ├── y: 7
       │   │   │   └── multiply/2/8/3/2 ⇒ succeeded 2019-01-01 17:27:13
       │   │   │       └── result: 7
       │   │   └── eliot:remote_task/2/8/4 ⇒ succeeded 2019-01-01 17:27:13
       │   ├── eliot:remote_task/2/9/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.001s
       │   │   ├── dask:task/2/9/2 2019-01-01 17:27:13
       │   │   │   ├── dependencies: 
       │   │   │   │   └── 0: map-multiply-75feec3a197bf253863e330f3483d3ac-1
       │   │   │   └── key: reduce-part-71950de8264334e8cea3cc79d1c2e639-1
       │   │   ├── multiply/2/9/3/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.000s
       │   │   │   ├── x: 2
       │   │   │   ├── y: 7
       │   │   │   └── multiply/2/9/3/2 ⇒ succeeded 2019-01-01 17:27:13
       │   │   │       └── result: 14
       │   │   └── eliot:remote_task/2/9/4 ⇒ succeeded 2019-01-01 17:27:13
       │   ├── eliot:remote_task/2/10/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.001s
       │   │   ├── dask:task/2/10/2 2019-01-01 17:27:13
       │   │   │   ├── dependencies: 
       │   │   │   │   └── 0: map-multiply-75feec3a197bf253863e330f3483d3ac-2
       │   │   │   └── key: reduce-part-71950de8264334e8cea3cc79d1c2e639-2
       │   │   ├── multiply/2/10/3/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.000s
       │   │   │   ├── x: 3
       │   │   │   ├── y: 7
       │   │   │   └── multiply/2/10/3/2 ⇒ succeeded 2019-01-01 17:27:13
       │   │   │       └── result: 21
       │   │   └── eliot:remote_task/2/10/4 ⇒ succeeded 2019-01-01 17:27:13
       │   ├── eliot:remote_task/2/11/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.001s
       │   │   ├── dask:task/2/11/2 2019-01-01 17:27:13
       │   │   │   ├── dependencies: 
       │   │   │   │   ├── 0: reduce-part-71950de8264334e8cea3cc79d1c2e639-0
       │   │   │   │   ├── 1: reduce-part-71950de8264334e8cea3cc79d1c2e639-1
       │   │   │   │   └── 2: reduce-part-71950de8264334e8cea3cc79d1c2e639-2
       │   │   │   └── key: reduce-aggregate-71950de8264334e8cea3cc79d1c2e639
       │   │   ├── add/2/11/3/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.000s
       │   │   │   ├── x: 7
       │   │   │   ├── y: 14
       │   │   │   └── add/2/11/3/2 ⇒ succeeded 2019-01-01 17:27:13
       │   │   │       └── result: 21
       │   │   ├── add/2/11/4/1 ⇒ started 2019-01-01 17:27:13 ⧖ 0.000s
       │   │   │   ├── x: 21
       │   │   │   ├── y: 21
       │   │   │   └── add/2/11/4/2 ⇒ succeeded 2019-01-01 17:27:13
       │   │   │       └── result: 42
       │   │   └── eliot:remote_task/2/11/5 ⇒ succeeded 2019-01-01 17:27:13
       │   └── dask:compute/2/12 ⇒ succeeded 2019-01-01 17:27:13
       └── main_computation/3 ⇒ succeeded 2019-01-01 17:27:13
           └── result: 42

.. warning::

   Retries within Dask will result in confusing log messages; this will eventually be fixed in a future release.
