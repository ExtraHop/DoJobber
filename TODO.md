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

Remove External Dependencies
----------------------------

Remove need for the following:

* dot binary (graphviz package)
* display binary (imagemagick package)
