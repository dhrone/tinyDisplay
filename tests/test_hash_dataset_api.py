import unittest
import base64
from tinyDisplay.utility.dataset import dataset

class TestHashDatasetAPI(unittest.TestCase):
    """Test the enhanced hash API features."""
    
    def test_hash_formats(self):
        """Test different hash output formats."""
        ds = dataset()
        ds.add("test_db", {"key1": "value1", "key2": "value2"})
        
        # Test different hash formats
        hex_hash = ds.get_hash("test_db", format='hex')
        bytes_hash = ds.get_hash("test_db", format='bytes')
        base64_hash = ds.get_hash("test_db", format='base64')
        
        # Verify that the formats are correct
        self.assertIsInstance(hex_hash, str)
        self.assertTrue(all(c in "0123456789abcdef" for c in hex_hash.lower()))
        
        self.assertIsInstance(bytes_hash, bytes)
        
        self.assertIsInstance(base64_hash, str)
        try:
            base64.b64decode(base64_hash)
        except Exception as e:
            self.fail(f"base64_hash is not a valid base64 string: {e}")
    
    def test_hash_comparison(self):
        """Test hash comparison between datasets."""
        # Create two identical datasets
        ds1 = dataset()
        ds2 = dataset()
        
        # Add identical data
        test_data = {"key1": "value1", "key2": "value2"}
        ds1.add("test_db", test_data)
        ds2.add("test_db", test_data)
        
        # Test hash comparison method
        self.assertTrue(ds1.compare_hash(ds2, "test_db"))
        
        # Modify one dataset
        ds2.update("test_db", {"key1": "modified"})
        
        # Comparison should now return False
        self.assertFalse(ds1.compare_hash(ds2, "test_db"))
    
    def test_hash_verification(self):
        """Test hash verification against expected values."""
        ds = dataset()
        ds.add("test_db", {"key1": "value1", "key2": "value2"})
        
        # Get hashes in different formats
        hex_hash = ds.get_hash("test_db", format='hex')
        bytes_hash = ds.get_hash("test_db", format='bytes')
        base64_hash = ds.get_hash("test_db", format='base64')
        
        # Test verification with correct hashes
        self.assertTrue(ds.verify_hash(hex_hash, "test_db", format='hex'))
        self.assertTrue(ds.verify_hash(bytes_hash, "test_db", format='bytes'))
        self.assertTrue(ds.verify_hash(base64_hash, "test_db", format='base64'))
        
        # Test verification with incorrect hashes
        incorrect_hex = "0" * len(hex_hash)
        incorrect_bytes = b"0" * len(bytes_hash)
        incorrect_base64 = base64.b64encode(b"0" * len(bytes_hash)).decode('ascii')
        
        self.assertFalse(ds.verify_hash(incorrect_hex, "test_db", format='hex'))
        self.assertFalse(ds.verify_hash(incorrect_bytes, "test_db", format='bytes'))
        self.assertFalse(ds.verify_hash(incorrect_base64, "test_db", format='base64'))
    
    def test_hash_invalidation(self):
        """Test explicit hash invalidation."""
        ds = dataset()
        ds.add("test_db", {"key1": "value1"})
        ds.add("other_db", {"key2": "value2"})
        
        # Get initial hashes
        initial_db_hash = ds.get_hash("test_db")
        initial_dataset_hash = ds.get_hash()
        
        # Invalidate hash for test_db
        ds.invalidate_hash("test_db")
        
        # The hash should be recalculated but should be the same since the data hasn't changed
        new_db_hash = ds.get_hash("test_db")
        new_dataset_hash = ds.get_hash()
        
        self.assertEqual(initial_db_hash, new_db_hash)
        self.assertEqual(initial_dataset_hash, new_dataset_hash)
        
        # Invalidate all hashes
        ds.invalidate_hash()
        
        # Again, hashes should be the same after recalculation
        all_new_db_hash = ds.get_hash("test_db")
        all_new_dataset_hash = ds.get_hash()
        
        self.assertEqual(initial_db_hash, all_new_db_hash)
        self.assertEqual(initial_dataset_hash, all_new_dataset_hash)
        
        # Modify the data and verify the hash changes
        ds.update("test_db", {"key1": "modified"})
        modified_db_hash = ds.get_hash("test_db")
        modified_dataset_hash = ds.get_hash()
        
        self.assertNotEqual(initial_db_hash, modified_db_hash)
        self.assertNotEqual(initial_dataset_hash, modified_dataset_hash)

if __name__ == "__main__":
    unittest.main()
