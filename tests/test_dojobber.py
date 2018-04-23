#!/usr/bin/env python
"""DoJobber Tests."""

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
        dojob.configure(doex.WatchMovie)
        dojob.set_args('arg1', movie='Noises Off', battery_state='dead')
        dojob.checknrun()
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

        # Verify our checknrun went as expected
        self.assertEqual(dojob.nodestatus, expected)
        self.assertFalse(dojob.success())

        # Verify our exception / return value handling is working
        self.assertEqual(str(dojob.nodeexceptions['TurnOnTV']),
                         "Remote batteries are dead.")

    def test_success_example(self):
        """Test our example dojobber that fully passes."""
        self.maxDiff = 999
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie)
        dojob.set_args(
            'arg1',
            movie='MST3K',
            battery_state='charged',
            couch_space=True)
        dojob.checknrun()
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
            'SitOnCouch': True,
            'StartMovie': True,
            'ValidateMovie': True,
            'TurnOnTV': True,
            'WatchMovie': True,
        }

        # Verify our checknrun went as expected
        self.assertEqual(dojob.nodestatus, expected)
        self.assertTrue(dojob.success())

    def test_runonly_node_succes(self):
        """Test that a runonly node with a successful Run works right."""
        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Succeed)
        dojob.checknrun()
        self.assertTrue(dojob.success())
        self.assertEqual(dojob.nodestatus, {'RunonlyTest_Succeed': True})
        self.assertEqual(dojob.noderesults['RunonlyTest_Succeed'],
                         'Mitchell!!!')

    def test_runonly_node_failure(self):
        """Test that a runonly node with a failing Run fails right."""

        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Fail)
        dojob.checknrun()
        self.assertFalse(dojob.success())
        self.assertEqual(dojob.nodestatus, {'RunonlyTest_Fail': False})
        self.assertEqual(str(dojob.nodeexceptions['RunonlyTest_Fail']),
                         'Are you with the bride or with the failure?')

    def test_runonly_node_no_act(self):
        """Test that a runonly node in no_act mode does not run the Run."""

        # A RunonlyJob that has a failing Run method
        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Fail, no_act=True)
        dojob.checknrun()
        self.assertEqual(dojob.nodestatus, {'RunonlyTest_Fail': False})
        self.assertEqual(str(dojob.nodeexceptions['RunonlyTest_Fail']),
                         'Runonly node check intentionally fails first time.')

        # A RunonlyJob that has a successful Run method should still fail
        # in no_act mode
        dojob = dojobber.DoJobber()
        dojob.configure(RunonlyTest_Succeed, no_act=True)
        dojob.checknrun()
        self.assertEqual(dojob.nodestatus, {'RunonlyTest_Succeed': False})
        self.assertEqual(str(dojob.nodeexceptions['RunonlyTest_Succeed']),
                         'Runonly node check intentionally fails first time.')

    def test_cleanran(self):
        """Test that our cleanup ran."""
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie)
        unittest_dict = {}
        dojob.set_args('arg1', unittest_dict=unittest_dict)
        dojob.checknrun()
        self.assertTrue(unittest_dict['duster_returned'])

    def test_clean_preventable(self):
        """Test that our cleanup can be prevented via configure."""
        dojob = dojobber.DoJobber()
        dojob.configure(doex.WatchMovie, cleanup=False)
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
        dojob.configure(doex.WatchMovie)
        dojob.set_args()
        dojob.checknrun()
        self.assertFalse(dojob.success())
        self.assertTrue(dojob.partial_success())

        dojob = dojobber.DoJobber()
        dojob.configure(doex.PrepareRoom)
        dojob.set_args()
        self.assertFalse(dojob.success())
        dojob.checknrun()
        self.assertTrue(dojob.success())
        self.assertTrue(dojob.partial_success())

        dojob = dojobber.DoJobber()
        dojob.configure(doex.TurnOnTV)
        dojob.set_args()
        dojob.checknrun()
        self.assertFalse(dojob.success())
        self.assertTrue(dojob.partial_success())


if __name__ == '__main__':
    unittest.main()
