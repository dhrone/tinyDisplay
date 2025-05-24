import unittest
from tinyDisplay.utility.dataset import dataset
from tinyDisplay.exceptions import ValidationError

class TestDatasetSchema(unittest.TestCase):
    """Test the schema validation functionality of the dataset class."""
    
    def test_basic_schema(self):
        """Test basic schema validation with simple types."""
        ds = dataset()
        
        # Register a simple schema
        ds.registerSchema("users", {
            "name": {"type": str, "required": True},
            "age": {"type": int, "validate": "_VAL_ >= 18", "default": 18},
            "email": {"type": str, "validate": lambda val: '@' in val, "default": "user@example.com"}
        })
        
        # Test with valid data
        update_data = {
            "name": "John Doe",
            "age": 25,
            "email": "john@example.com"
        }
        # Validate and apply the update directly
        validated_update = ds.validateUpdate("users", update_data)
        ds.update("users", validated_update)
        
        self.assertEqual(ds._dataset["users"]["name"], "John Doe")
        self.assertEqual(ds._dataset["users"]["age"], 25)
        self.assertEqual(ds._dataset["users"]["email"], "john@example.com")
        
        # Test with invalid data (age < 18)
        invalid_data = {
            "name": "Jane Doe",
            "age": 16,
            "email": "jane@example.com"
        }
        # Validate and apply the update directly
        validated_invalid = ds.validateUpdate("users", invalid_data)
        ds.update("users", validated_invalid)
        
        # Should use default value for age
        self.assertEqual(ds._dataset["users"]["name"], "Jane Doe")
        self.assertEqual(ds._dataset["users"]["age"], 18)
        self.assertEqual(ds._dataset["users"]["email"], "jane@example.com")
        
        # Test with invalid data (email without @)
        invalid_email_data = {
            "name": "Bob Smith",
            "age": 30,
            "email": "invalid-email"
        }
        # Validate and apply the update
        validated_invalid_email = ds.validateUpdate("users", invalid_email_data)
        ds.update("users", validated_invalid_email)
        
        # Should use default value for email
        self.assertEqual(ds._dataset["users"]["name"], "Bob Smith")
        self.assertEqual(ds._dataset["users"]["age"], 30)
        self.assertEqual(ds._dataset["users"]["email"], "user@example.com")
        
        # Test with missing required field
        missing_required_data = {
            "age": 35,
            "email": "test@example.com"
        }
        # Validate and apply the update
        validated_missing = ds.validateUpdate("users", missing_required_data)
        ds.update("users", validated_missing)
        
        # Should keep previous value for name (required field)
        self.assertEqual(ds._dataset["users"]["name"], "Bob Smith")
        self.assertEqual(ds._dataset["users"]["age"], 35)
        self.assertEqual(ds._dataset["users"]["email"], "test@example.com")
        
    def test_nested_schema(self):
        """Test schema validation with nested structures."""
        ds = dataset()
        
        # Register a schema with nested structure
        ds.registerSchema("products", {
            "name": {"type": str, "required": True},
            "price": {"type": float, "validate": "_VAL_ > 0", "default": 9.99},
            "attributes": {
                "type": dict,
                "schema": {
                    "color": {"type": str, "default": "black"},
                    "size": {
                        "type": str, 
                        "validate": lambda val: val in ['S', 'M', 'L', 'XL'],
                        "default": "M"
                    }
                }
            }
        })
        
        # Test with valid data
        nested_data = {
            "name": "T-Shirt",
            "price": 19.99,
            "attributes": {
                "color": "blue",
                "size": "L"
            }
        }
        # Validate and apply the update
        validated_nested = ds.validateUpdate("products", nested_data)
        ds.update("products", validated_nested)
        
        self.assertEqual(ds._dataset["products"]["name"], "T-Shirt")
        self.assertEqual(ds._dataset["products"]["price"], 19.99)
        self.assertEqual(ds._dataset["products"]["attributes"]["color"], "blue")
        self.assertEqual(ds._dataset["products"]["attributes"]["size"], "L")
        
        # Test with invalid nested data
        invalid_nested_data = {
            "name": "Jeans",
            "price": 39.99,
            "attributes": {
                "color": "denim",
                "size": "XXL"  # Invalid size
            }
        }
        # Validate and apply the update
        validated_invalid_nested = ds.validateUpdate("products", invalid_nested_data)
        ds.update("products", validated_invalid_nested)
        
        # Should use default value for size
        self.assertEqual(ds._dataset["products"]["name"], "Jeans")
        self.assertEqual(ds._dataset["products"]["price"], 39.99)
        self.assertEqual(ds._dataset["products"]["attributes"]["color"], "denim")
        self.assertEqual(ds._dataset["products"]["attributes"]["size"], "M")
        
    def test_array_schema(self):
        """Test schema validation with array items."""
        ds = dataset()
        
        # Register a schema with array items
        ds.registerSchema("posts", {
            "title": {"type": str, "required": True},
            "content": {"type": str},
            "tags": {
                "type": list,
                "items": {
                    "type": str,
                    "validate": lambda val: len(val) > 0
                }
            },
            "comments": {
                "type": list,
                "items": {
                    "type": dict,
                    "schema": {
                        "author": {"type": str, "required": True},
                        "text": {"type": str, "required": True}
                    }
                }
            }
        })
        
        # Test with valid data
        array_data = {
            "title": "My First Post",
            "content": "Hello, world!",
            "tags": ["hello", "first", "post"],
            "comments": [
                {"author": "John", "text": "Great post!"},
                {"author": "Jane", "text": "Thanks for sharing!"}
            ]
        }
        # Validate and apply the update
        validated_array = ds.validateUpdate("posts", array_data)
        ds.update("posts", validated_array)
        
        self.assertEqual(ds._dataset["posts"]["title"], "My First Post")
        self.assertEqual(ds._dataset["posts"]["content"], "Hello, world!")
        self.assertEqual(len(ds._dataset["posts"]["tags"]), 3)
        self.assertEqual(len(ds._dataset["posts"]["comments"]), 2)
        
        # Test with invalid array items
        invalid_array_data = {
            "title": "Updated Post",
            "tags": ["valid", "", "also-valid"],  # Empty string is invalid
            "comments": [
                {"author": "Alice", "text": "Nice update!"},
                {"text": "Missing author field"}  # Missing required field
            ]
        }
        # Validate and apply the update
        validated_invalid_array = ds.validateUpdate("posts", invalid_array_data)
        ds.update("posts", validated_invalid_array)
        
        # Should filter out invalid items
        self.assertEqual(ds._dataset["posts"]["title"], "Updated Post")
        self.assertEqual(len(ds._dataset["posts"]["tags"]), 2)  # Empty tag filtered out
        self.assertEqual(len(ds._dataset["posts"]["comments"]), 1)  # Invalid comment filtered out
        
    def test_type_conversion(self):
        """Test automatic type conversion in schema validation."""
        ds = dataset()
        
        # Register schema with various types
        ds.registerSchema("config", {
            "name": {"type": str},
            "enabled": {"type": bool},
            "count": {"type": int},
            "factor": {"type": float},
            "options": {"type": [str, int]}  # Multiple allowed types
        })
        
        # Test with values that need conversion
        ds.update("config", {
            "name": 123,  # Should convert to "123"
            "enabled": "true",  # Should convert to True
            "count": "42",  # Should convert to 42
            "factor": "3.14",  # Should convert to 3.14
            "options": 3.14  # Should convert to either string or int
        })
        
        self.assertEqual(ds._dataset["config"]["name"], "123")
        self.assertEqual(ds._dataset["config"]["enabled"], True)
        self.assertEqual(ds._dataset["config"]["count"], 42)
        self.assertEqual(ds._dataset["config"]["factor"], 3.14)
        self.assertTrue(isinstance(ds._dataset["config"]["options"], (str, int)))
        
    def test_debug_mode(self):
        """Test schema validation in debug mode."""
        ds = dataset()
        ds._debug = True
        
        # Register a simple schema
        ds.registerSchema("test", {
            "required_field": {"type": str, "required": True}
        })
        
        # Test with missing required field
        with self.assertRaises(ValidationError):
            ds.update("test", {"optional_field": "value"})
            
if __name__ == "__main__":
    unittest.main()
