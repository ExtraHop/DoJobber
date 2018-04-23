TODO
====

A list of potential future improvements

Flesh Out README
----------------

The dojobber_example.py has lots of great comments, but the big
picture and individual examples need to move here.

Dynamic Nodes
-------------

Make dynamically adding nodes more developer-friendly. Currently you
can use this pattern

* make a base class that has self.FOO variables that control what it does
* instantiate a new class based on it and override the FOO variables
* add the new class to one or more Job's self.DEPS variables

This works, but it would be better to have this as something you can
call via the dojobber.DoJobber object itself, which would make it
cleaner and easier to unit test, for example.

Python3 Support
---------------

Python3 support shouldn't be terribly hard, we just haven't started it yet.

Remove External Dependencies
----------------------------

Remove need for the following:

* dot binary (graphviz package)
* display binary (imagemagick package)

Retries
-------

Some Jobs may execute quickly, but the results will not be accurate
immediately. For example you may make an API call to a remote system
and it may take time for it to complete, and until it's done the
Check will fail.

Implement a retry option, where processing can continue on any
non-blocked Jobs, once those are exhausted you start retrying any
retry-able Jobs, with a sleep inbetween if you run out. This
will prevent us from needing to re-run the entire script
when the delays are out of our control.

Proposed retry inputs: max time to retry, min time between retries.
