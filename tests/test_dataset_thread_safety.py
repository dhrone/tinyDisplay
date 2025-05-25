#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for thread safety in the dataset class.
"""

import unittest
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from tinyDisplay.utility.dataset import dataset


class TestDatasetThreadSafety(unittest.TestCase):
    """Test cases for dataset thread safety."""

    def setUp(self):
        """Set up test fixtures."""
        self.ds = dataset(thread_safe=True)
        # Register validation for individual fields with the correct API
        self.ds.registerValidation("test", key="counter", type="int", default=0)
        self.ds.registerValidation("config", key="name", type="str", default="test")
        self.ds.setDefaults()

    def test_concurrent_updates(self):
        """Test that concurrent updates to the dataset are thread-safe."""
        num_threads = 20
        updates_per_thread = 50
        
        # Function to update the dataset from multiple threads
        def update_counter(thread_id):
            results = []
            for i in range(updates_per_thread):
                # Get current value
                with self.ds.with_lock() as locked_ds:
                    current = locked_ds.get("test", {}).get("counter", 0)
                    # Update the value atomically
                    locked_ds.update("test", {"counter": current + 1})
                    results.append(current + 1)
                # Small random sleep to increase chance of race conditions
                time.sleep(random.uniform(0.001, 0.005))
            return results
            
        # Run updates concurrently
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(update_counter, i) for i in range(num_threads)]
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
                
        # Check that the final counter value is correct
        final_counter = self.ds.get("test", {}).get("counter", 0)
        expected_count = num_threads * updates_per_thread
        self.assertEqual(final_counter, expected_count, 
                         f"Expected counter to be {expected_count}, got {final_counter}")
        
        # Check that we have the right number of unique values
        unique_values = set(all_results)
        self.assertEqual(len(unique_values), expected_count, 
                         "Each update should result in a unique counter value")

    def test_transaction_thread_safety(self):
        """Test that transactions are thread-safe across multiple threads."""
        num_threads = 10
        transactions_per_thread = 20
        
        # Initial state
        self.ds.update("accounts", {
            "user1": {"balance": 1000},
            "user2": {"balance": 1000}
        })
        
        # Simulate a transfer between accounts that must be atomic
        def transfer_funds(thread_id):
            successes = 0
            for i in range(transactions_per_thread):
                # Transfer a random amount between accounts
                amount = random.randint(10, 50)
                
                # Use a transaction to ensure atomicity
                with self.ds.transaction() as tx:
                    # Read current balances
                    user1_balance = tx.get("accounts", {}).get("user1", {}).get("balance", 0)
                    user2_balance = tx.get("accounts", {}).get("user2", {}).get("balance", 0)
                    
                    # Update balances
                    tx.update("accounts", {
                        "user1": {"balance": user1_balance - amount},
                        "user2": {"balance": user2_balance + amount}
                    })
                    
                    # Transaction will automatically commit if no exceptions occur
                    successes += 1
                    
                # Small sleep to increase chance of race conditions
                time.sleep(random.uniform(0.001, 0.01))
                
            return successes
            
        # Run transfers concurrently
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(transfer_funds, i) for i in range(num_threads)]
            successful_transfers = sum(future.result() for future in as_completed(futures))
            
        # Check final balances
        final_user1 = self.ds.get("accounts", {}).get("user1", {}).get("balance", 0)
        final_user2 = self.ds.get("accounts", {}).get("user2", {}).get("balance", 0)
        
        # Verify that total balance is preserved
        self.assertEqual(final_user1 + final_user2, 2000, 
                         "Total balance should remain constant after transfers")
        
        # Verify that all transactions were applied
        self.assertEqual(successful_transfers, num_threads * transactions_per_thread,
                         "All transactions should succeed")

    def test_batch_update_thread_safety(self):
        """Test that batch updates are thread-safe across multiple threads."""
        num_threads = 10
        batches_per_thread = 20
        
        # Create counters for each thread
        for i in range(num_threads):
            self.ds.update("counters", {f"thread_{i}": 0})
        
        # Function to perform batch updates
        def perform_batch_updates(thread_id):
            results = []
            for i in range(batches_per_thread):
                # Get current values for all counters this thread will update
                counters_to_update = {}
                for j in range(3):  # Update 3 random counters in each batch
                    counter_id = f"thread_{random.randint(0, num_threads-1)}"
                    current = self.ds.get("counters", {}).get(counter_id, 0)
                    counters_to_update[counter_id] = current + 1
                
                # Perform batch update
                self.ds.batch_update({
                    "counters": counters_to_update,
                    "metadata": {f"last_update_by": f"thread_{thread_id}"}
                })
                
                results.append(len(counters_to_update))
                time.sleep(random.uniform(0.001, 0.005))
            
            return sum(results)
        
        # Run batch updates concurrently
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(perform_batch_updates, i) for i in range(num_threads)]
            total_counter_updates = sum(future.result() for future in as_completed(futures))
            
        # Calculate the sum of all counter values
        total_counter_sum = sum(self.ds.get("counters", {}).get(f"thread_{i}", 0) for i in range(num_threads))
        
        # Verify that all updates were applied correctly
        self.assertEqual(total_counter_sum, total_counter_updates,
                         "Total counter sum should match total updates applied")

    def test_concurrent_reads_during_updates(self):
        """Test that reads are consistent during concurrent updates."""
        num_update_threads = 5
        num_read_threads = 15
        updates_per_thread = 50
        reads_per_thread = 100
        
        # Function for threads that update the dataset
        def update_dataset(thread_id):
            for i in range(updates_per_thread):
                # Update multiple values atomically
                self.ds.update("data", {
                    f"key_{thread_id}_{i}": i,
                    "counter": thread_id * updates_per_thread + i
                })
                time.sleep(random.uniform(0.001, 0.003))
            return True
        
        # Function for threads that read from the dataset
        def read_dataset(thread_id):
            consistent_reads = 0
            for i in range(reads_per_thread):
                # Get the current data
                data = self.ds.get("data", {})
                counter = data.get("counter", 0)
                
                # Check for data consistency - if counter exists, the corresponding key should also exist
                if counter > 0:
                    update_thread = counter // updates_per_thread
                    update_index = counter % updates_per_thread
                    expected_key = f"key_{update_thread}_{update_index}"
                    
                    if expected_key in data and data[expected_key] == update_index:
                        consistent_reads += 1
                
                time.sleep(random.uniform(0.001, 0.002))
            
            return consistent_reads
        
        # Create initial data
        self.ds.update("data", {"counter": 0})
        
        # Run both update and read threads concurrently
        with ThreadPoolExecutor(max_workers=num_update_threads + num_read_threads) as executor:
            update_futures = [executor.submit(update_dataset, i) for i in range(num_update_threads)]
            read_futures = [executor.submit(read_dataset, i) for i in range(num_read_threads)]
            
            # Wait for updates to complete
            for future in as_completed(update_futures):
                assert future.result()
                
            # Get read consistency results
            consistent_read_count = sum(future.result() for future in as_completed(read_futures))
            
        # Print consistency statistics
        total_reads = num_read_threads * reads_per_thread
        self.assertGreater(consistent_read_count, 0, 
                           "Should have at least some consistent reads")
        
        print(f"Read consistency: {consistent_read_count}/{total_reads} "
              f"({consistent_read_count/total_reads:.2%}) reads were consistent")


if __name__ == "__main__":
    unittest.main()
