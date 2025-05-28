import unittest
from tinyDisplay.utility.dataset import dataset

class TestDatasetValidation(unittest.TestCase):
    """Test the enhanced validation system in the dataset class."""
    
    def test_string_based_validation(self):
        """Test string-based validation (DSL compatibility)."""
        ds = dataset()
        
        # Register string-based validation
        ds.registerValidation(
            dbName="users",
            key="age",
            type="int",
            validate="_VAL_ >= 18",
            default=18
        )
        
        # The database and key already exist with default value after registration
        self.assertEqual(ds._dataset["users"]["age"], 18)
        
        # Update with valid data
        ds.update("users", {"age": 25})
        self.assertEqual(ds._dataset["users"]["age"], 25)
        
        # Update with invalid data (should use default)
        ds.update("users", {"age": 15})
        self.assertEqual(ds._dataset["users"]["age"], 18)
        
        # Test type conversion
        ds.update("users", {"age": "30"})
        self.assertEqual(ds._dataset["users"]["age"], 30)
        self.assertIsInstance(ds._dataset["users"]["age"], int)
    
    def test_lambda_based_validation(self):
        """Test lambda-based validation (programmatic use)."""
        ds = dataset()
        
        # Register lambda-based validation
        ds.registerValidation(
            dbName="emails",
            key="address",
            type=str,
            validate=lambda val: '@' in val,
            default="user@example.com"
        )
        
        # The database and key already exist with default value after registration
        self.assertEqual(ds._dataset["emails"]["address"], "user@example.com")
        
        # Update with valid data
        ds.update("emails", {"address": "john@example.com"})
        self.assertEqual(ds._dataset["emails"]["address"], "john@example.com")
        
        # Update with invalid data (should use default)
        ds.update("emails", {"address": "invalid-email"})
        self.assertEqual(ds._dataset["emails"]["address"], "user@example.com")
    
    def test_multiple_types(self):
        """Test validation with multiple allowed types."""
        ds = dataset()
        
        # Register validation with multiple types
        ds.registerValidation(
            dbName="config",
            key="value",
            type=[int, str],
            default="default"
        )
        
        # Test with integer
        ds.update("config", {"value": 42})
        self.assertEqual(ds._dataset["config"]["value"], 42)
        
        # Test with string
        ds.update("config", {"value": "text"})
        self.assertEqual(ds._dataset["config"]["value"], "text")
        
        # Test with float (should be converted to string since it's not in allowed types)
        ds.update("config", {"value": 3.14})
        # Check if it's either a string or an int (depending on implementation)
        value = ds._dataset["config"]["value"]
        self.assertTrue(isinstance(value, str) or isinstance(value, int), 
                        f"Expected str or int, got {type(value)}")
    
    def test_onupdate_callback(self):
        """Test onUpdate callbacks."""
        ds = dataset()
        
        # String-based onUpdate
        ds.registerValidation(
            dbName="counter",
            key="value",
            type="int",
            onUpdate="_VAL_ * 2",
            default=0
        )
        
        # Lambda-based onUpdate
        ds.registerValidation(
            dbName="counter",
            key="squared",
            type="int",
            onUpdate=lambda val: val * val,
            default=0
        )
        
        # Update and check transformation
        ds.update("counter", {"value": 5, "squared": 4})
        self.assertEqual(ds._dataset["counter"]["value"], 10)  # 5 * 2
        self.assertEqual(ds._dataset["counter"]["squared"], 16)  # 4 * 4
    
    def test_database_level_validation(self):
        """Test database-level validation."""
        ds = dataset()
        
        # Register database-level validation
        ds.registerValidation(
            dbName="settings",
            validate=lambda val: "theme" in val,
            default={"theme": "default"}
        )
        
        # Valid update
        ds.update("settings", {"theme": "dark", "fontSize": 14})
        self.assertEqual(ds._dataset["settings"]["theme"], "dark")
        
        # Invalid update
        ds.update("settings", {"fontSize": 16})
        self.assertEqual(ds._dataset["settings"]["theme"], "default")
    
    def test_complex_validation(self):
        """Test complex validation with multiple rules."""
        ds = dataset()
        
        # Register validation with multiple rules
        ds.registerValidation(
            dbName="user",
            key="password",
            type=str,
            validate=[
                lambda val: len(val) >= 8,  # Min length
                lambda val: any(c.isdigit() for c in val),  # Contains digit
                lambda val: any(c.isupper() for c in val)   # Contains uppercase
            ],
            default="Default1"
        )
        
        # Valid password
        ds.update("user", {"password": "Secure123"})
        self.assertEqual(ds._dataset["user"]["password"], "Secure123")
        
        # Invalid password (too short)
        ds.update("user", {"password": "Abc123"})
        self.assertEqual(ds._dataset["user"]["password"], "Default1")
        
        # Invalid password (no uppercase)
        ds.update("user", {"password": "secure123"})
        self.assertEqual(ds._dataset["user"]["password"], "Default1")
        
        # Invalid password (no digit)
        ds.update("user", {"password": "SecurePass"})
        self.assertEqual(ds._dataset["user"]["password"], "Default1")

if __name__ == "__main__":
    unittest.main()
