import ruff  # Install using pip install ruff
# Importing pytest requires it to be installed as well
import pytest

def calculate_sum(a, b):
    result = a + b
    print("The sum is: ", str(result))
    return result

def greet(name):
    message = f"Hello, {name}"
    print(message)
    return message

# Test cases for the functions
def test_calculate_sum():
    assert calculate_sum(5, 7) == 12

def test_greet_name():
    name = "Joshua"
    result = greet(name)
    assert isinstance(result, str)

# Run tests when this script is executed
pytest.main([__file__])