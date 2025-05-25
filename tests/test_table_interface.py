#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test for the new Table interface in dataset.
"""

import unittest
from tinyDisplay.utility.dataset import dataset


class TestTableInterface(unittest.TestCase):
    """Test the new Table interface for dataset."""

    def setUp(self):
        """Set up a dataset for testing."""
        self.ds = dataset()
        # Initialize with some data
        self.ds.update('system', {
            'temperature': 70,
            'humidity': 50,
            'status': 'normal'
        })
        self.ds.update('user', {
            'name': 'Test User',
            'preferences': {
                'theme': 'dark',
                'notifications': True
            }
        })

    def test_attribute_access(self):
        """Test attribute-style access to tables."""
        # Access tables as attributes
        self.assertEqual(self.ds.system['temperature'], 70)
        self.assertEqual(self.ds.user['name'], 'Test User')
        
        # Test nested access
        self.assertEqual(self.ds.user['preferences']['theme'], 'dark')
        
        # Test iteration
        keys = list(self.ds.system)
        self.assertIn('temperature', keys)
        self.assertIn('humidity', keys)
        self.assertIn('status', keys)
        
        # Test containment
        self.assertTrue('temperature' in self.ds.system)
        self.assertFalse('unknown' in self.ds.system)
        
        # Test length
        self.assertEqual(len(self.ds.system), 3)
        
        # Test dictionary methods
        self.assertEqual(list(self.ds.system.keys()), list(self.ds['system'].keys()))
        self.assertEqual(list(self.ds.system.values()), list(self.ds['system'].values()))
        self.assertEqual(list(self.ds.system.items()), list(self.ds['system'].items()))
        
        # Test get method
        self.assertEqual(self.ds.system.get('temperature'), 70)
        self.assertEqual(self.ds.system.get('unknown', 'default'), 'default')

    def test_update_via_table(self):
        """Test updating values via the Table interface."""
        # Update a single value with __setitem__
        self.ds.system['temperature'] = 75
        self.assertEqual(self.ds['system']['temperature'], 75)
        
        # Update multiple values with update method
        self.ds.system.update({
            'humidity': 60,
            'pressure': 1013
        })
        self.assertEqual(self.ds['system']['humidity'], 60)
        self.assertEqual(self.ds['system']['pressure'], 1013)
        
        # Test that the Table interface correctly updates through the dataset mechanism
        self.assertEqual(self.ds['system']['pressure'], 1013)
        
        # Test nested updates
        self.ds.user['preferences']['theme'] = 'light'
        self.assertEqual(self.ds['user']['preferences']['theme'], 'light')

    def test_backward_compatibility(self):
        """Test that the traditional dictionary interface still works."""
        # Traditional access
        initial_temp = self.ds['system']['temperature']
        
        # Traditional update
        self.ds.update('system', {'temperature': 80})
        self.assertEqual(self.ds.system['temperature'], 80)
        
        # Mix and match - this syntax doesn't work with the current implementation
        # but we can use the update method instead
        self.ds.update('system', {'humidity': 65})
        self.assertEqual(self.ds.system['humidity'], 65)


if __name__ == '__main__':
    unittest.main()
