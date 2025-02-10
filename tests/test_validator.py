import unittest
from hangoutsscheduler.utils.validator import MessageValidator

class TestMessageValidator(unittest.TestCase):

    def setUp(self):
        self.validator = MessageValidator(max_tokens=5)

    def test_validate_message_within_limit(self):
        message = "This is a test"
        result = self.validator.validate_message(message)
        self.assertEqual(result, message)

    def test_validate_message_exceeds_limit(self):
        message = "This is a test message that exceeds the limit"
        expected_result = "This is a test message"
        result = self.validator.validate_message(message)
        self.assertEqual(result, expected_result)

    def test_validate_message_exact_limit(self):
        message = "One two three four five"
        result = self.validator.validate_message(message)
        self.assertEqual(result, message)

if __name__ == '__main__':
    unittest.main()
