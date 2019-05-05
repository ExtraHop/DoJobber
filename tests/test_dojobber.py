#!/usr/bin/env python
"""DoJobber Tests."""

import logging
import more_tests
import unittest
import dojobber
import dojobber_example as doex

## We like lint, but DoJobber classes get much longer
## if we implement all of the normal best practices
# pylint:disable=invalid-name
# pylint:disable=missing-docstring
#  # pylint:disable=no-init
#  # pylint:disable=no-self-use
#  # pylint:disable=too-few-public-methods
#  # pylint:disable=unused-argument



class RunonlyTest_Fail(dojobber.RunonlyJob):
    def Run(self, *dummy_args, **dummy_kwargs):
        raise RuntimeError('Are you with the bride or with the failure?')


class RunonlyTest_Succeed(dojobber.RunonlyJob):
    def Run(self, *dummy_args, **dummy_kwargs):
        return 'Mitchell!!!'


class Tests(unittest.TestCase):

    def test_default_example(self):
        """Test our example dojobber test results that have some failures."""
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        dojob.set_args('arg1', movie='Noises Off', battery_state='dead')
        dojob.checknrun()
        expected = {
            'CleanCouch': True,
            'DetermineDetails': True,
            'FindTVRemote': True,
            'FluffPillows': True,
            'Food': True,
            'FriendsArrive': True,
            'InsertDVD': True,
            'InviteFriends': True,
            'PickTimeAndDate': True,
            'Pizza': True,
            'Popcorn': True,
            'PopcornBowl': True,
            'PrepareRoom': True,
            'SitOnCouch': False,
            'StartMovie': None,
            'ValidateMovie': True,
            'TurnOnTV': False,
            'WatchMovie': None,
        }

        # Verify our checknrun went as expected
        self.assertEqual(expected, dojob.nodestatus)
        self.assertFalse(dojob.success())

        # Verify our exception / return value handling is working
        self.assertEqual("Remote batteries are dead.",
                         str(dojob.nodeexceptions['TurnOnTV']))

    def test_success_example(self):
        """Test our example dojobber that fully passes."""
        self.maxDiff = 9999
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        dojob.set_args(
            'arg1',
            movie='MST3K',
            battery_state='charged',
            couch_space=True,
            fake_retry_success=True)
        dojob.checknrun()
        expected = {
            'CleanCouch': True,
            'DetermineDetails': True,
            'FindTVRemote': True,
            'FluffPillows': True,
            'Food': True,
            'FriendsArrive': True,
            'InsertDVD': True,
            'InviteFriends': True,
            'PickTimeAndDate': True,
            'Pizza': True,
            'Popcorn': True,
            'PopcornBowl': True,
            'PrepareRoom': True,
            'SitOnCouch': True,
            'StartMovie': True,
            'ValidateMovie': True,
            'TurnOnTV': True,
            'WatchMovie': True,
        }

        # Verify our checknrun went as expected
        self.assertEqual(expected, dojob.nodestatus)
        self.assertTrue(dojob.success())

    def test_runonly_node_succes(self):
        """Test that a runonly node with a successful Run works right."""
        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Succeed, default_retry_delay=0)
        dojob.checknrun()
        self.assertTrue(dojob.success())
        self.assertEqual({'RunonlyTest_Succeed': True}, dojob.nodestatus)
        self.assertEqual('Mitchell!!!',
                         dojob.noderesults['RunonlyTest_Succeed'])

    def test_runonly_node_failure(self):
        """Test that a runonly node with a failing Run fails right."""

        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Fail, default_retry_delay=0, default_tries=1.1)
        dojob.checknrun()
        self.assertFalse(dojob.success())
        self.assertEqual({'RunonlyTest_Fail': False}, dojob.nodestatus)
        self.assertEqual('Are you with the bride or with the failure?',
                         str(dojob.nodeexceptions['RunonlyTest_Fail']))

    def test_runonly_node_no_act(self):
        """Test that a runonly node in no_act mode does not run the Run."""

        # A RunonlyJob that has a failing Run method
        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Fail, no_act=True)
        dojob.checknrun()
        self.assertEqual({'RunonlyTest_Fail': False}, dojob.nodestatus)
        self.assertEqual('Runonly node check intentionally fails first time.',
                         str(dojob.nodeexceptions['RunonlyTest_Fail']))

        # A RunonlyJob that has a successful Run method should still fail
        # in no_act mode
        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Succeed, no_act=True)
        dojob.checknrun()
        self.assertEqual({'RunonlyTest_Succeed': False}, dojob.nodestatus)
        self.assertEqual('Runonly node check intentionally fails first time.',
                         str(dojob.nodeexceptions['RunonlyTest_Succeed']))

    def test_cleanran(self):
        """Test that our cleanup ran."""
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        unittest_dict = {}
        dojob.set_args('arg1', unittest_dict=unittest_dict)
        dojob.checknrun()
        self.assertTrue(unittest_dict['duster_returned'])

    def test_clean_preventable(self):
        """Test that our cleanup can be prevented via configure."""
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, cleanup=False, default_retry_delay=0)
        unittest_dict = {}
        dojob.set_args('arg1', unittest_dict=unittest_dict)
        dojob.checknrun()
        self.assertFalse(unittest_dict.get('duster_returned'))

        # Now verify we can run it manually
        dojob.cleanup()
        self.assertTrue(unittest_dict['duster_returned'])

    def test_success_conditions(self):
        """Test our success checks based on some example subgraphs."""
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        dojob.set_args()
        dojob.checknrun()
        self.assertFalse(dojob.success())
        self.assertTrue(dojob.partial_success())

        dojob = dojobber.DoJobber()
        dojob.configure(doex.PrepareRoom, default_retry_delay=0)
        dojob.set_args()
        self.assertFalse(dojob.success())
        dojob.checknrun()
        self.assertTrue(dojob.success())
        self.assertTrue(dojob.partial_success())

        dojob = dojobber.DoJobber()
        dojob.configure(doex.TurnOnTV, default_retry_delay=0)
        dojob.set_args()
        dojob.checknrun()
        self.assertFalse(dojob.success())
        self.assertTrue(dojob.partial_success())

    def test_retry(self):
        """Test our example dojobber and tweak when retries succeed."""
        expected = {
            'CleanCouch': True,
            'DetermineDetails': True,
            'FindTVRemote': True,
            'FluffPillows': True,
            'FriendsArrive': True,
            'InsertDVD': True,
            'InviteFriends': True,
            'PickTimeAndDate': True,
            'PrepareRoom': True,
            'SitOnCouch': False,
            'StartMovie': None,
            'ValidateMovie': True,
            'TurnOnTV': False,
            'WatchMovie': None,
        }

        # Everything succeeds
        expected.update({'Food': True, 'Pizza': True,
                         'PopcornBowl': True, 'Popcorn': True})
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        dojob.set_args('arg1', movie='Noises Off', battery_state='dead',
                pizza_success_try=doex.Pizza.TRIES,
                pop_success_try=doex.Popcorn.TRIES,
                bowl_success_try=doex.PopcornBowl.TRIES)
        dojob.checknrun()
        self.assertEqual(expected, dojob.nodestatus)

        # PopcornBowl, the first node, fails.
        expected.update({'Food': None, 'Pizza': True,
                         'PopcornBowl': False, 'Popcorn': None})
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        dojob.set_args('arg1', movie='Noises Off', battery_state='dead',
                pizza_success_try=doex.Pizza.TRIES,
                pop_success_try=doex.Popcorn.TRIES,
                bowl_success_try=doex.PopcornBowl.TRIES + 1)
        dojob.checknrun()
        self.assertEqual(expected, dojob.nodestatus)

        # Popcorn, the second node, fails
        expected.update({'Food': None, 'Pizza': True,
                         'PopcornBowl': True, 'Popcorn': False})
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        dojob.set_args('arg1', movie='Noises Off', battery_state='dead',
                pizza_success_try=doex.Pizza.TRIES,
                pop_success_try=doex.Popcorn.TRIES + 1,
                bowl_success_try=doex.PopcornBowl.TRIES)
        dojob.checknrun()
        self.assertEqual(expected, dojob.nodestatus)

        # Fail our Pizza and Popcorn
        expected.update({'Food': None, 'Pizza': False,
                         'PopcornBowl': True, 'Popcorn': False})
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, default_retry_delay=0)
        dojob.set_args('arg1', movie='Noises Off', battery_state='dead',
                pizza_success_try=doex.Pizza.TRIES + 1,
                pop_success_try=doex.Popcorn.TRIES + 1,
                bowl_success_try=doex.PopcornBowl.TRIES)
        dojob.checknrun()
        self.assertEqual(expected, dojob.nodestatus)

    def test_brokeninit(self):
        """Verify that a broken Job __init__ doesn't kill processing."""
        expected = {
            'BrokenInit': False,
            'Passful': True,
            'Top00': None,
        }
        dojob = dojobber.DoJobber(dojobber_loglevel=logging.NOTSET)
        dojob.configure(more_tests.Top00, default_retry_delay=0, default_tries=1)
        dojob.checknrun()
        self.assertEqual(expected, dojob.nodestatus)


if __name__ == '__main__':
    unittest.main()
