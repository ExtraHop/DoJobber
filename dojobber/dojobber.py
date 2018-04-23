#!/usr/bin/env python
"""DoJobber Class."""

# standard
import os
import sys
import traceback
import subprocess
import distutils.spawn

from pygraph.algorithms import cycles
from pygraph.algorithms.searching import depth_first_search
from pygraph.classes.digraph import digraph


# Determine if we have external dependencies to generate/show graphs
try:
    import pygraph.readwrite.dot as dot
except ImportError:
    sys.stderr.write('** Graphs will not be supported'
                     ' (cannot import pygraph.readwrite.dot - pip install )\n')
    dot = None
if dot and not distutils.spawn.find_executable('dot'):
    dot = None
    sys.stderr.write('** Graphs will not be supported'
                     ' (no dot executable - install graphviz)\n')
DISPLAY = True
if not distutils.spawn.find_executable('display'):
    DISPLAY = False
    sys.stderr.write('** display_graph will not be supported'
                     ' (no display executable - install imagemagick.\n')

## Disable some pylint warnings
# pylint:disable=invalid-name
# pylint:disable=too-few-public-methods


class Job(object):
    """Job Class."""

    def __init__(self):  # pylint:disable=super-init-not-called
        """Initialization.

        attributes:
            storage - the local storage, used between Check/Run executions
            global_storage - global checknrun storage

            _check_phase - either 'check' or 'recheck', depending on if this
                          the first check or the post-Run check.
                          In general you should not do anything different
                          based on check or recheck, but this could be useful
                          for mocks and other trickery.

            _check_results - the result of the Check, if succesful, else None
            _check_exception - the exception from Check, if unsuccessful, else None
            _run_results - the result of the Run, if successful, else None
            _run_exception - the exception from the Run, if unsuccessful, else None
            _recheck_results - the result of the re-Check, if succesful, else None
            _recheck_exception - the exception from re-Check, if unsuccessful, else None
        """

        self.storage = None
        self.global_storage = None

        # These are provided for advanced Check/Run methods.
        # Using these is not actually advisable - if all your
        # work is idempontent, this is unnecessary. May break
        # at any time. YMMV. HAND. OMGWTFBBQ.
        self._check_phase = None
        self._check_results = None
        self._check_exception = None
        self._run_results = None
        self._run_exception = None
        self._recheck_results = None
        self._recheck_exception = None

    def _set_storage(self, storage, global_storage):
        """Set the storage dictionaries.

        These are set by the DoJobber.
        storage is used for storing state between checks and runs of the
        same Job. It is initialized at each check/run/check phase.

        global_storage is shared between all nodes in a DoJobber run.
        It is up to the Job authors to play nicely with each other
        in storing and retrieving data from this dictionary. Best practice
        is to create a subdictionary with your node name, e.g.

          self.global_storage['MyNodeClass']['something'] = value

        global_storage is initialized on
        and made availablet
        """
        self.storage = storage
        self.global_storage = global_storage


class RunonlyJob(Job):
    """A Job that only does the 'run' phase.

    This node will run your Run method exactly
    once. If it does not raise an exception,
    we consider that a pass.

    You *MUST NOT* include a Check method to your class.

    Even though you do not provide a Check, we run all
    Check/Run/Check phases. The initial Check always fails,
    causing your Run to execute. On success, the final
    Check will return the Run method's results; on failure
    the final Check will raise the Run method's exception.

    When your DoJobber was configured with no_act=True,
    your Check will always fail since we cannot verify
    if the Run would succeed without actually running it.

    Example Usage:

      class ShellSomething(RunonlyJob):
          def Run(self, *args, **kwargs):
              code = subprocess.call(['/usr/bin/userdel', 'wendellbagg'])
              if code != 1:
                  raise RuntimeError('run failed!')
    """
    _run_err = None

    def Check(self, *_, **dummy_kwargs):
        """Fail if Run not run, else return Run result."""
        if self._check_phase == 'check':
            raise RuntimeError(
                'Runonly node check intentionally fails first time.')
        else:
            if self._run_exception:
                raise self._run_exception  # pylint:disable=raising-bad-type
            else:
                return self._run_results


class DummyJob(Job):
    """A Job with no Check nor Run, always succeeds.

    Useful for creating a node that only has dependencies.
    """

    def Check(self, *dummy_args, **dummy_kwargs):
        """Always pass."""
        pass

    def Run(self, *dummy_args, **dummy_kwargs):
        """Always pass."""
        pass


class DoJobber(object):
    """DoJobber Class."""

    def __init__(self):  # pylint:disable=super-init-not-called
        """Initialization."""
        self.graph = digraph()
        self.nodestatus = {}
        self.nodeexceptions = {}
        self.noderesults = {}

        self._args = []  # Args for Check/Run methods
        self._kwargs = {}  # KWArgs for Check/Run methods
        self._root = None  # Root Job
        self._checknrun_cwd = None
        self._checknrun_storage = None
        self._classmap = {}  # map of name: actual_class_obj
        self._cleanup = True  # Should we automatically do a cleanup
        self._verbose = False
        self._debug = False
        self._no_act = False
        self._deps = {}
        self._objsrun = []  # which objects ran, for triggering Cleanup

    def cleanup(self):
        """Run all Cleanup methods for nodes that ran, LIFO.

        Any Cleanup method that raises an exception will halt
        processing - attempting to be 'smart' and figure out
        which Cleanup problems are safe to ignore is not our job.

        This is called automatically by checknrun at completion
        time, unless you explicitly used cleanup=False in configure()
        """
        for obj in reversed(self._objsrun):
            if callable(getattr(obj, 'Cleanup', None)):
                if self._debug:
                    sys.stderr.write(
                        '{}.cleanup running\n'.format(
                            type(obj).__name__))
                try:
                    obj.Cleanup()
                    if self._debug:
                        sys.stderr.write(
                            '{}.cleanup: pass\n'.format(
                                type(obj).__name__))
                except Exception as err:
                    sys.stderr.write(
                        '{}.cleanup: fail "{}"\n'.format(
                            type(obj).__name__, err))
                    raise

    def partial_success(self):
        """Returns T/F if any checknrun nodes were succesfull."""
        return self.nodestatus and any(self.nodestatus.values())

    def success(self):
        """Returns T/F if the checknrun hit all nodes with 100% success."""
        return self.nodestatus and all(self.nodestatus.values())

    def failure(self):
        """Returns T/F if the checknrun had any failure nodes."""
        return not self.success()

    def configure(self, root, no_act=False, verbose=False, debug=False,
                  cleanup=True):
        """Configure the graph for a specified root Job.

        no_act: only run Checks, do not make changes (i.e. no Run)
        verbose: show a line per check/run/recheck, including recheck
                 failure output
        debug: show full stacktrace on failure of check/run/recheck
        cleanup: run any Cleanup methods on classes once checknrun is complete
        """
        self._no_act = no_act
        self._debug = debug
        self._verbose = self._debug or verbose
        self._root = root
        self._load_class()
        self._cleanup = cleanup

    def set_args(self, *args, **kwargs):
        """Set the arguments that will be sent to all Check/Run methods."""
        self._args = args
        self._kwargs = kwargs

    def _class_name(self, theclass):  # pylint:disable=no-self-use
        """Returns a class from a class or string rep."""
        if isinstance(theclass, str):
            return theclass
        return theclass.__name__

    def _node_failed(self, nodename, err):
        """Update graph and attributes for failed node."""
        self.graph.add_node_attribute(nodename, ('style', 'filled'))
        self.graph.add_node_attribute(nodename, ('color', 'red'))
        self.nodestatus[nodename] = False
        self.nodeexceptions[nodename] = err

    def _node_succeeded(self, nodename, results):
        """Update graph and attributes for successful node."""
        self.nodestatus[nodename] = True
        self.graph.add_node_attribute(nodename, ('style', 'filled'))
        self.graph.add_node_attribute(nodename, ('color', 'green'))
        self.noderesults[nodename] = results

    def _node_eventually_succeeded(self, nodename, results):
        """Update graph and attributes for eventually successful node."""
        self.nodestatus[nodename] = True
        self.graph.add_node_attribute(nodename, ('style', 'filled'))
        self.graph.add_node_attribute(nodename, ('color', 'darkgreen'))
        self.noderesults[nodename] = results

    def _node_untested(self, nodename):
        """Update graph and attributes for untested node."""
        self.nodestatus[nodename] = None

    def checknrun(self, node=None):
        """Check and run each class.

        This method initializes the storage and launches
        the actual checknrun routines.

        Environmental concerns

          Your routines SHOULD not create any unexpected side effects,
          but there are things that may not be expected and handled.

          Current working directory
            We'll remember where checknrun is called.
            Before each Check and Run, we'll cd back here.
            We'll also cd back here before returning.

          Environment
            We do not currently preserve environment modifications.
            You shouldn't do them. Future versions will sanitize
            between runs.
        """
        self._checknrun_cwd = os.path.realpath(os.curdir)
        self._checknrun_storage = {'__global': {}}
        self.nodestatus = {}
        self._checknrun(node)
        os.chdir(self._checknrun_cwd)
        if self._cleanup:
            self.cleanup()

    def _checknrun(self, node=None):  # pylint:disable=too-many-branches
        """Check and run each class.

        Assumes all storage and other initialization is complete already.
        """
        # pylint:disable=protected-access

        if not node:
            node = self._root
        nodename = self._class_name(node)
        _, _, post = depth_first_search(self.graph, root=nodename)

        # Run dependent nodes and see if all were successful
        blocked = False
        for depnode in post:
            if depnode == nodename:
                continue

            # Run them
            if self.nodestatus.get(depnode, None) is None:
                self._checknrun(depnode)

            # Were they happy?
            if not self.nodestatus.get(depnode, None):
                blocked = True

        self._node_untested(nodename)
        if not blocked:
            obj = self._classmap[nodename]()
            self._checknrun_storage[nodename] = {}
            obj._set_storage(
                self._checknrun_storage[nodename],
                self._checknrun_storage['__global'])
            self._objsrun.append(obj)

            # check / run / check
            try:
                os.chdir(self._checknrun_cwd)
                obj._check_phase = 'check'
                obj._check_results = obj.Check(*self._args, **self._kwargs)
                self._node_succeeded(nodename, obj._check_results)
                if self._verbose:
                    sys.stderr.write(
                        '{}.check: pass\n'.format(nodename))
            except Exception as err:  # pylint:disable=broad-except
                obj._check_exception = err
                if self._verbose:
                    sys.stderr.write('%s.check: fail\n' % nodename)

                # In no_act mode, we only run the first check
                # and get out of dodge.
                if self._no_act:
                    self._node_failed(nodename, err)
                    if self._debug:
                        sys.stderr.write(
                            '  Error was:\n  '
                            '{}\n'.format(traceback.format_exc().strip()
                                          .replace('\n', '\n  ')))
                    return

                # Run the Run method, which may fail with
                # wild abandon - we'll be doing a recheck anyway.
                try:
                    os.chdir(self._checknrun_cwd)
                    obj._run_results = obj.Run(*self._args, **self._kwargs)
                    if self._verbose:
                        sys.stderr.write('%s.run: pass\n' % nodename)
                except Exception as err:  #pylint:disable=broad-except
                    obj._run_exception = err
                    if self._verbose:
                        sys.stderr.write('%s.run: fail\n' % nodename)
                    if self._debug:
                        sys.stderr.write(
                            '  Error was:\n  '
                            '{}\n'.format(traceback.format_exc().strip()
                                          .replace('\n', '\n  ')))

                # Do a recheck
                try:
                    os.chdir(self._checknrun_cwd)
                    obj._check_phase = 'recheck'
                    obj._recheck_results = obj.Check(*self._args, **self._kwargs)
                    self._node_eventually_succeeded(nodename, obj._recheck_results)
                    if self._verbose:
                        sys.stderr.write('%s.recheck: pass\n' % nodename)
                except Exception as err:  # pylint:disable=broad-except
                    obj._recheck_exception = err
                    if self._verbose:
                        sys.stderr.write('%s.recheck: fail "%s"\n' %
                                         (nodename, err))
                    if self._debug:
                        sys.stderr.write(
                            '  Error was:\n  {}\n'.format(
                                traceback.format_exc().strip()
                                .replace('\n', '\n  ')))
                    self._node_failed(nodename, err)

    def _load_class(self):
        """Generate internal graph for a checkrun class."""

        self._init_deps(self._root)
        self._init_graph()

    def _dot_output(self, fmt='png'):
        """Run dot with specified output format and return output."""

        command = ['dot', '-T%s' % fmt]
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            )
        stdout, _ = proc.communicate(dot.write(self.graph))

        if proc.returncode != 0:
            raise RuntimeError(
                'Cannot create dot graphs via {}'.format(' '.join(command)))

        return stdout

    def write_graph(self, filed, fmt='png'):
        """Write a graph to the filedescriptor with named format.

        Format must be something understood as a 'dot -Tfmt' argument.

        Raises Error on dot command failure.
        """
        if not dot:
            return

        filed.write(self._dot_output(fmt))

    def display_graph(self):
        """Show the dot graph to X11 screen."""
        if not all((dot, DISPLAY)):
            return

        image_content = self._dot_output()
        proc = subprocess.Popen(['display'], stdin=subprocess.PIPE)
        proc.communicate(image_content)
        if proc.returncode != 0:
            raise RuntimeError('Cannot show graph using "display"')

    def _init_graph(self):
        """Initialize our graph."""
        for classname in self._classmap:
            for dep in self._deps[classname]:
                self.graph.add_edge((classname, dep))
        if cycles.find_cycle(self.graph):
            raise RuntimeError(
                'Programmer error: graph contains cycles "{}"'.format(
                    cycles.find_cycle(self.graph)))

    def _init_deps(self, theclass):
        """Initialize our dependencies."""

        classname = self._class_name(theclass)
        if classname in self._classmap:
            return

        self._classmap[classname] = theclass
        self.graph.add_node(classname)
        deps = getattr(theclass, 'DEPS', [])

        for dep in deps:
            self._init_deps(dep)

        self._deps[classname] = [self._class_name(x) for x in deps]


if __name__ == '__main__':
    sys.exit('This is a library only')
