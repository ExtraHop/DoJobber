
DoJobber
========

DoJobber is a python task orchestration framework based on writing
small single-task idempotent classes (Jobs), defining
interdependencies, and letting python do all the work of running
them in the "right order".

DoJobber builds an internal graph of Jobs. It will run
Jobs that have no unmet dependencies, working up the chain
until it either reaches the root or cannot go further due to
Job failures.

Each Job serves a single purpose, and must be idempotent, 
i.e. it will produce the same results if executed once or
multiple times, without causing any unintended side effects.
Because of this you can run your python script multiple times
and it will get closer and closer to completion as any
previously-failed Jobs succeed.

Here's an example of how one might break down the overall
goal of inviting friends over to watch a movie - this
is the result of the ``tests/dojobber_example.py`` script.

    .. image:: https://raw.githubusercontent.com/extrahop-networks/DoJobber/master/example.png
        :alt: DoJobber example graph
        :width: 90%
        :align: center

Rather than a yaml-based syntax with many plugins, DoJobber
lets you write in native python, so anything you can code
you can plumb into the DoJobber framework.

DoJobber is conceptually based on a Google program known as
Masher that was built for automating service and datacenter
spinups, but shares no code with it.


Job Structure
=============

Each Job is is own class. Here's an example::

    class FriendsArrive(Job):
        DEPS = (InviteFriends,)

        def Check(self, *dummy_args, **dummy_kwargs):
            # Do something to verify that everyone has arrived.
            pass

        def Run(self, *dummy_args, **dummy_kwargs):
            pass

Each Job has a DEPS variable, ``Check`` method, and ``Run`` method.

DEPS
----

DEPS defines which other Jobs it is dependent on. This is used
for generating the internal graph.


Check
-----
``Check`` executes and, if it does not raise an Exception, is considered
to have passed. If it passes then the Job passed and the next Job will
run. It's purpose is to verify that we are in the desired state for
this Job. For example if the job was to create a user, this may
look up the user in /etc/passwd.

Run
---

``Run`` executes if ``Check`` failed. Its job is to do something to achieve
our goal. DoJobber doesn't care if it returns anything, throws an
exception, or exits - all this is ignored.

An example might be creating a user account, or adding a database
entry, or launching an ansible playbook.

Recheck
-------

The Recheck phase simply executes the ``Check`` method again. Hopefully
the ``Run`` method did the work that was necessary, so ``Check`` will verify
all is now well. If so (i.e. ``Check`` does not raise an Exception) then
we consider this Job a success, and any dependent Jobs are not blocked
from running.

Job Features
============

Job Arguments
-------------

Jobs can take both positional and keyword arguments. These are set via the
set_args method::

    dojob = dojobber.DoJobber()
    dojob.configure(RootJob, ......)
    dojob.set_args('arg1', 'arg2', foo='foo', bar='bar', ...)

Because of this it is best to accept both in your ``Check`` and ``Run`` methods::

    def Check(self, *args, **kwargs):
        ....

    def Run(self, *args, **kwargs):
        ....

If you're generating your keyword arguments from argparse or optparse,
then you can be even lazier - send it in as a dict::

    myparser = argparse.ArgumentParser()
    myparser.add_argument('--movie', dest='movie', help='Movie to watch.')
    ...
    args = myparser.parse_args()
    dojob.set_args(**args.__dict__)

An then in your ``Check``/``Run`` you can use them by name::

    def Check(self, *args, **kwargs):
        if kwargs['movie'] == 'Zardoz':
            raise Error('Really?')


Storage (local)
---------------

TBD

Storage (global)
---------------

TBD

Cleanup
-------

Jobs can have a Cleanup method. After checknrun is complete,
the Cleanup method of each Job that ran (i.e. ``Run`` was executed)
will be excuted. They are run in LIFO order, so Cleanups 'unwind'
everything.

You can pass the cleanup=False option to DoJobber() to prevent
Cleanup from happening and run it manually if you prefer::

    dojob = dojobber.DoJobber()
    dojob.configure(RootJob, cleanup=False, ......)
    dojob.checknrun()
    dojob.cleanup()

Creating Jobs Dynamically
-------------------------

TBD

Job Types
=========

There are several DoJobber Job types:

Job
---

Job requires a ``Check``, ``Run``, and may have optional Cleanup::
    
    class CreateUser(Job):
        """Create our user's account."""

        def Check(self, *_, **kwargs):
            """Verify the user exists"""
            import pwd
            pwd.getpwnam(kwargs['username'])

        def Run(self, *_, **kwargs):
            """Create user given the commandline username/gecos arguments"""
            import subprocess
            subprocess.call([
                'sudo', '/usr/sbin/adduser',
                '--shell', '/bin/tcsh',
                '--gecos', kwargs['gecos'],
                kwargs['username'])

        ### Optional Cleanup method
        #def Cleanup(self):
        #   """Do something to clean up."""
        #   pass

DummyJob
--------

DummyJob  has no ``Check``, ``Run``, nor Cleanup. It is used simply to
have a Job for grouping dependent or dynamically-created Jobs.


So a DummyJob may look as simple as this::

    class PlaceHolder(DummyJob):
        DEPS = (Dependency1, Dependency2, ...)


RunonlyJob
----------

A ``RunonlyJob`` has no check, just a ``Run``, which will run every time.

If ``Run`` raises an exception then the Job is considered failed.

They cannot succeed in no_act mode, because
in this mode the ``Run`` is never executed.

So an example ``Run`` may look like this::

    class RemoveDangerously(RunonlyJob):
        DEPS = (UserAcceptedTheConsequences,)

        def Run(...):
            os.system('rm -rf /')

In general, avoid ``RunonlyJob``s - it's better if you can understand if
a change even needs making.

Examples
========

The ``tests/dojobber_example.py`` script in the source directory is
fully-functioning suite of tests with numerous comments strewn
throughout.

