#!/usr/bin/env python
"""DoJobber Test.

This is an example of DoJobber in action. The
scenario is of getting some friends together to
watch a movie.

This file is used by the dojobber_test for unit test
purposes, so do not change it unless its related to
testing new functionality.

Information is strewn throughout comments and docstrings.
Enjoy!
"""

import argparse
import logging
import os
import sys

import dojobber
# These 'from...imports' just decrease typing when making your classes
from dojobber import Job
from dojobber import DummyJob
from dojobber import RunonlyJob

## We like lint, but DoJobber classes get much longer
## if we implement all of the normal best practices
# pylint:disable=missing-docstring
# pylint:disable=no-init
# pylint:disable=no-self-use
# pylint:disable=too-few-public-methods
# pylint:disable=unused-argument
# pylint:disable=invalid-name


# This import is used as part of this contrived
# example - not needed for general DoJobber use.
import random


AVAILABLE_MOVIES = [
    'Noises Off',
    'MST3K',
    'Babylon 5'
]


class CleanCouch(Job):
    """CleanCouch's check fails first time only.

    An example of using Job storage - the right way
    to maintain some local state.
    """
    DEPS = ()

    def Check(self, *dummy_args, **dummy_kwargs):
        if not self.storage.get('runran'):
            raise ValueError('I fail unless run runs....')

    def Run(self, *dummy_args, **kwargs):
        self.storage['runran'] = True

        # This code is just for unit testing purposes, you can ignore it.
        self.global_storage['unittest_dict'] = kwargs.get('unittest_dict', {})

    def Cleanup(self):
        """This method should clean up any side effects of Check or Run.

        Cleanup methods are to be avoided because there's no guarantee
        that they'll be run, for example if another Cleanup raises an exception.

        Useful for cleaning up local temp files, git checkouts, etc.
        """
        logging.info('Putting away the feather duster in CleanCouch.Cleanup.')

        # Set a global storage value for unit testing purposes
        self.global_storage['unittest_dict']['duster_returned'] = True


class FindTVRemote(Job):
    """Find the remote."""
    DEPS = ()

    def Check(self, *dummy_args, **dummy_kwargs):
        pass

    def Run(self, *dummy_args, **dummy_kwargs):
        pass


class FluffPillows(RunonlyJob):
    """FluffPillows will *always* (re)fluff the pillows.

    As a RunonlyJob, there is no need for a "check", this is essentially
    a "fire and forget".

    This is only useful if the action (pillow fluffing) is idempotent
    and will not cause unintended side effects, and we have no way to
    verify that the action is not necessary.
    """
    DEPS = ()

    def Run(self, *dummy_args, **dummy_kwargs):
        """If this method fails, then the entire Job fails."""
        logging.info('I am fluffing the pillows in FluffPillows.Run.')


class PickTimeAndDate(Job):
    """Pick a movie time from our list, store for use later

    Shows how you can set global state which is used by another Job.
    """
    TIMES = ('2024-04-08 18:18 UTC',
             '2099-09-14 16:57 UTC')

    def Check(self, *dummy_args, **dummy_kwargs):
        # Only successful if we've set our start time
        assert self.global_storage['Start-DateTime']

    def Run(self, *dummy_args, **dummy_kwargs):
        timechoice = random.choice(self.TIMES)
        self.global_storage['Start-DateTime'] = timechoice


class ValidateMovie(Job):
    """Validate the movie requested is available, based on user input.

    We get the choice from the kwargs, and verify its one
    of the movies we have available on our shelf.
    """

    def Check(self, *dummy_args, **kwargs):
        if kwargs.get('movie') not in AVAILABLE_MOVIES:
            raise RuntimeError('{} not one of the available movies.'.format(
                kwargs.get('movie')))

    def Run(self, *dummy_args, **dummy_kwargs):
        pass


class InsertDVD(Job):
    """Insert the DVD into the player.

    We show how you can use a Cleanup method.

    In our example this would be closing up the DVD case and putting it back
    on the shelf where you can find it again.
    """
    DEPS = (ValidateMovie,)

    def Check(self, *dummy_args, **dummy_kwargs):
        pass

    def Run(self, *dummy_args, **dummy_kwargs):
        pass


class PrepareRoom(DummyJob):
    """PrepareRoom is just a DummyJob."""
    DEPS = (CleanCouch, FluffPillows)


class PopcornBowl(DummyJob):
    """Get a popcorn bowl from the dishwasher

    This example includes TRIES and RETRY_DELAY options.

    TRIES defines the number of tries (check/run/recheck cycles)
    that the Job is allowed to do before giving up.

    The TRIES default if unspecified is 3, which can be changed
    in configure() via the default_tries=### argument.

    RETRY_DELAY is the minimum amount of time to wait between
    tries of *this* Job.

    The RETRY_DELAY default if unspecified is 3, which can be changed
    in configure() via the default_retry_delay=### argument.

    When a Job has a failure it is not immediately retried.
    Instead we will hit all Jobs in the graph that are still
    awaiting check/run/recheck. Once every reachabel Job has
    been hit we will 'start over' on the Jobs that failed.

    In practice this means that you aren't wasting as much
    RETRY_DELAY because other Jobs were likely doing work
    between retries of this Job. (Unless your graph is
    highly linear and there are no unblocked Jobs.)
    """
    TRIES = 8  # The default is 1, i.e. no retries
    RETRY_DELAY = 0.001

    def Check(self, *_, **kwargs):
        # Simulate failures and eventual successes
        success_try = kwargs.get('bowl_success_try') or self.TRIES
        if self.global_storage.get('bowl_failcount', 0) < success_try:
            raise RuntimeError("Dishwasher cycle not done yet.")

    def Run(self, *_, **kwargs):
        self.global_storage['bowl_failcount'] = (
            self.global_storage.get('bowl_failcount', 0) + 1)


class Pizza(RunonlyJob):
    """Get pizza.

    In reality this would make no sense as a RunonlyJob, however
    it is implemented this way here for unit testing purposes.
    """
    TRIES = 3

    def Run(self, *_, **kwargs):
        # Simulate failures and eventual successes
        self.global_storage['pizza_failcount'] = (
            self.global_storage.get('pizza_failcount', 0) + 1)
        success_try = kwargs.get('pizza_success_try') or self.TRIES
        if self.global_storage.get('pizza_failcount', 0) < success_try:
            raise RuntimeError("Giordano's did not arrive yet.")


class Popcorn(Job):
    """Get Popcorn.

    Does retries, similar to Pizza above.
    """
    DEPS = (PopcornBowl,)
    # Popcorn.TRIES is intentionally lower than PopcornBowl.TRIES so
    # we assure through unit tests that our retry counting logic is
    # based on individual Job retries, not on global Job retries.
    TRIES = PopcornBowl.TRIES - 3

    def Check(self, *_, **kwargs):
        # Simulate failures and eventual successes
        success_try = kwargs.get('pop_success_try') or self.TRIES
        if self.global_storage.get('pop_failcount', 0) < success_try:
            raise RuntimeError('Still popping...')

    def Run(self, *_, **kwargs):
        self.global_storage['pop_failcount'] = (
            self.global_storage.get('pop_failcount', 0) + 1)


class Food(DummyJob):
    """Get noshies."""
    DEPS = (Popcorn, Pizza)


class SitOnCouch(Job):
    """Sit on the couch."""
    DEPS = (PrepareRoom,)

    def Check(self, *_, **kwargs):
        if not kwargs.get('couch_space'):
            raise RuntimeError('No space on couch.')

    def Run(self, *_, **kwargs):
        pass


class DetermineDetails(DummyJob):
    """DeterminDetails is just a DummyJob."""
    DEPS = (ValidateMovie, PickTimeAndDate)


class InviteFriends(DummyJob):
    """InviteFriends is a DummyJob that grows over time.

    This class exists only to have dependencies. It doesn't do anything
    itself, and thus needs no Check or Run.

    You should not use it for checking success/failure of other Jobs,
    but rather for optimizations, for example an expensive initialization
    that may need to be done in many Jobs. Have one Job do this
    work and store the results, and have others depend on it and save
    the repeated work.
    """
    DEPS = [DetermineDetails,]  # This will be expanded by invite_friends
    INVITE = None


class SendInvite(Job):
    """Send an invite to someone.

    This Job is not run directly (i.e. it is not in DEPS for any other Job)
    but instead is used to generate Jobs dynamically via the invitation_job
    function.

    You inherit from this and set self.{EMAIL,NAME} and add it to the
    DEPS of the Job where it belongs. See invitation_job for example.
    """
    EMAIL = None
    NAME = None
    DEPS = (DetermineDetails,)
    SENT = False

    def Check(self, *_, **dummy_kwargs):
        """Check to see if we sent an email

        In real code, you'd need some way to know you
        sent the invite. Perhaps this would be an API call
        to your invite tool, or check your 'sent' email for
        a message to the person with the expected details..

        In this example we'll just verify that Run ran at all.

        Essentially, this is a RunonlyJob wearing other clothing.
        """
        assert self.SENT

    def Run(self, *_, **kwargs):
        """Send the email

        We pick up the name and email from our class variables,
        and we pick up the movie choice and start time from
        global storage.
        """
        content = 'Come and watch {} at {} with me!'.format(
            kwargs['movie'],
            self.global_storage['Start-DateTime'])
        recipient = '{} <{}>'.format(self.NAME, self.EMAIL)

        # Do something to send the invite. Here's an example
        #  if we were using smtp
        #
        #msg = MIMEText(content)
        #msg['Subject'] = 'Come watch a movie with me!'
        #msg['To'] = recipient
        #smtp = smtplib.SMTP(host='localhost'
        #smtp.sendmail(
        #    os.environ.get('USER') + '@example.com',
        #    [self.EMAIL]
        #    msg.as_string())
        logging.info('Sent {} the following: \n\t{}\n'.format(
            recipient, content))
        self.SENT = True


def invite_friends(people):
    """Create new invitation jobs

    This function creates new Jobs based on the SendInvite Job and adds
    them to the DEPS of the InviteFriends Job, thus causing them to appear
    in our list and be executed.
    """
    for person in people:
        job = type('Invite {}'.format(person['name']), (SendInvite,), {})
        job.EMAIL = person['email']
        job.NAME = person['name']
        InviteFriends.DEPS.append(job)


class FriendsArrive(Job):
    DEPS = (InviteFriends,)

    def Check(self, *dummy_args, **dummy_kwargs):
        # Do something to verify that everyone has arrived.
        pass

    def Run(self, *dummy_args, **dummy_kwargs):
        pass


class TurnOnTV(Job):
    """Example: show how to receive keyword values.

    TurnOnTV passes as long as it gets the right value from
    keyword args. In our example, this is that the batteries
    actually have power still.

    Unfortunately, they don't. ;-)
    """
    DEPS = (FindTVRemote,)

    def Check(self, *dummy_args, **kwargs):
        if kwargs['battery_state'] != 'charged':
            raise RuntimeError('Remote batteries are dead.')

    def Run(self, *dummy_args, **dummy_kwargs):
        # Take out bateries, put them back in
        # Might that fix it?
        # Pretend we did something here....
        pass


class StartMovie(Job):
    DEPS = (FriendsArrive, PrepareRoom, TurnOnTV, InsertDVD, SitOnCouch, Food)

    def Check(self, *dummy_args, **dummy_kwargs):
        pass

    def Run(self, *dummy_args, **dummy_kwargs):
        pass


class WatchMovie(Job):
    DEPS = (StartMovie,)

    def Check(self, *dummy_args, **dummy_kwargs):
        pass

    def Run(self, *dummy_args, **dummy_kwargs):
        pass

def handle_args():
    """Parse our arguments, return args result."""
    myparser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    myparser.add_argument(
        '-n', '--no-act', dest='no_act',
        action='store_true',
        help='Do Checks only, make no changes.')

    group = myparser.add_argument_group('Display/Output Options')
    # Verbose mode will output all check/run statuses in a terse mode
    group.add_argument('-v', dest='verbose', action='store_true',
                       help='Verbose DoJobber output.')

    # Debug will output full stack trace of all check/run failures
    group.add_argument('-d', dest='debug', action='store_true',
                       help='Debug DoJobber output.')

    # Debug will output full stack trace of all check/run failures
    group.add_argument('--app-logs', dest='app_logs', action='store_true',
        help='Enable example log output. (Not same as DoJobber output, -v/-d)')

    # By default we'll display x11 graphs when we think they'll work.
    # Use --no-x11 if you don't have imagemagick installed or
    # your DISPLAY is lying.
    group.add_argument(
        '--x11', dest='x11', action='store_true',
        default=True,
        help='Try to display result graphs on X11 display')
    group.add_argument(
        '--no-x11', dest='x11', action='store_const',
        const=False,
        help='Do not try to display result graphs on X11 display')

    group.add_argument(
        '--display_prerungraph', dest='display_prerungraph',
        action='store_true',
        help='Display the Job graph prior to doing anything.')

    # No X11 but you want to see the results image? Save it to
    # a file then.
    group.add_argument(
        '--png_output', dest='png_output',
        help='Write the results graph in png form to the given filename')

    group = myparser.add_argument_group(title='Example Input Tweaking')
    # Allow user to pick a movie. We add one that's not available
    # such that you can test a failure via '--movie Zardoz'
    group.add_argument(
        '--movie', dest='movie',
        help='Movie to watch.',
        default=AVAILABLE_MOVIES[0],
        choices=AVAILABLE_MOVIES + ['Zardoz'])

    group.add_argument(
        '--battery_state', dest='battery_state',
        help='Faux TV Remote Battery State. Try "charged" to make them work.',
        default='dead')

    group.add_argument(
        '--couch_space', dest='couch_space',
        action='store_true',
        help='There is room on the couch for you to sit.',)

    group = myparser.add_argument_group(
        title='Retry Testing',
        description='Try values higher than the max tries to see failures'
                    ' or smaller to succeed sooner. Best with -v so you can'
                    ' see how unblocked Jobs are retried interleaved rather'
                    ' than repeatedly.')
    group.add_argument(
        '--pop_success_try', dest='pop_success', type=int, metavar='#',
        help='Achieve sucess on the Popcorn Job at this number of tries.'
             ' By default this contrived example will succeed on the last try.'
             ' Values higher than {} will cause this to fail, so you can test'
             ' the retry logic.'.format(Popcorn.TRIES))

    group.add_argument(
        '--bowl_success_try', dest='bowl_success', type=int, metavar='#',
        help='Achieve sucess on the PopcornBowl Job at this number of tries.'
             ' By default this contrived example will succeed on the last try.'
             ' Values higher than {} will cause this to fail, so you can test'
             ' the retry logic.'.format(PopcornBowl.TRIES))

    group.add_argument(
        '--pizza_success_try', dest='pizza_success_try', type=int, metavar='#',
        help='Achieve sucess on the Pizza Job at this number of tries.'
             ' By default this contrived example will succeed on the last try.'
             ' Values higher than {} will cause this to fail, so you can test'
             ' the retry logic.'.format(Pizza.TRIES))

    # Parsing time!
    args = myparser.parse_args()

    # Enable logging from the Jobs themselves if we're in debug mode
    if args.app_logs:
        logging.basicConfig(level=logging.INFO)

    # Determine if we should show graphs
    args.x11 = True if os.environ.get('DISPLAY') and args.x11 else False

    return args


def main():
    args = handle_args()

    # Add individual friend invite Jobs to our InviteFriends Job list.
    # Pretend these came from command line args, or a database, or whatever.
    invite_friends([
        {'name': 'Wendell Bagg', 'email': 'bagg@example.com'},
        {'name': 'Lawyer Cat', 'email': 'lawyercat@example.com'},
    ])

    dojob = dojobber.DoJobber()
    dojob.configure(
        WatchMovie,
        no_act=args.no_act,
        verbose=args.verbose,
        default_retry_delay=0,
        debug=args.debug)

    ## Since all our argument names are the same as the kwargs keys,
    ## we can simply send in the args dictionary as-is.
    dojob.set_args(**args.__dict__)

    ## If you wanted to do it manually, then you could do it similar to this:
    #
    # dojob.set_args(
    #    movie=args.movie,
    #    battery_state=args.battery_state,
    #    couch_space=args.couch_space)

    if args.x11 and args.display_prerungraph:
        dojob.display_graph()

    # Run our checks/runs and clean up when done
    dojob.checknrun()

    if args.x11:
        dojob.display_graph()

    if args.png_output:
        out = open(args.png_output, 'w')
        dojob.write_graph(out)

    sys.exit(0 if dojob.success() else 1)


if __name__ == '__main__':
    main()
