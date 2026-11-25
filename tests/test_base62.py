import unittest

from src.base62 import decode, encode


class Base62Test(unittest.TestCase):
    def test_encode_known_values(self):
        cases = (
            (0, "0"),
            (1, "1"),
            (9, "9"),
            (10, "a"),
            (35, "z"),
            (36, "A"),
            (61, "Z"),
            (62, "10"),
        )
        for number, expected in cases:
            with self.subTest(number=number):
                self.assertEqual(encode(number), expected)

    def test_decode_known_values(self):
        cases = (
            ("0", 0),
            ("1", 1),
            ("9", 9),
            ("a", 10),
            ("z", 35),
            ("A", 36),
            ("Z", 61),
            ("10", 62),
        )
        for encoded, expected in cases:
            with self.subTest(encoded=encoded):
                self.assertEqual(decode(encoded), expected)

    def test_boundary_values(self):
        for number in (62, 63, 3844, 10_000, 62**20):
            with self.subTest(number=number):
                self.assertEqual(decode(encode(number)), number)

    def test_encode_rejects_negative_numbers(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_encode_rejects_non_integer_values(self):
        for value in (None, 1.5, "62", True):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode(value)

    def test_decode_rejects_empty_string(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_decode_rejects_non_string_values(self):
        for value in (None, 62, 62.0, ["10"]):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    decode(value)

    def test_decode_rejects_invalid_characters(self):
        for value in ("-", "_", "10+", " 10", "한"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode(value)

    def test_round_trip_many_values(self):
        values = (0, 1, 61, 62, 123, 1_000, 62**3, 62**10 - 1)
        for number in values:
            with self.subTest(number=number):
                self.assertEqual(decode(encode(number)), number)


if __name__ == "__main__":
    unittest.main()
