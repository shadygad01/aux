"""Tests for the shared domain from_dict coercion helpers."""

from __future__ import annotations

import unittest

from packages.domain._json_coerce import to_float, to_int


class ToFloatTests(unittest.TestCase):
    def test_accepts_int_float_and_numeric_string(self) -> None:
        self.assertEqual(to_float(5), 5.0)
        self.assertEqual(to_float(5.5), 5.5)
        self.assertEqual(to_float("5.5"), 5.5)

    def test_rejects_bool(self) -> None:
        with self.assertRaises(TypeError):
            to_float(True)

    def test_rejects_non_numeric_type(self) -> None:
        with self.assertRaises(TypeError):
            to_float(None)
        with self.assertRaises(TypeError):
            to_float([1, 2])


class ToIntTests(unittest.TestCase):
    def test_accepts_int_float_and_numeric_string(self) -> None:
        self.assertEqual(to_int(5), 5)
        self.assertEqual(to_int(5.9), 5)
        self.assertEqual(to_int("5"), 5)

    def test_rejects_bool(self) -> None:
        with self.assertRaises(TypeError):
            to_int(True)

    def test_rejects_non_numeric_type(self) -> None:
        with self.assertRaises(TypeError):
            to_int(None)
        with self.assertRaises(TypeError):
            to_int({"a": 1})


if __name__ == "__main__":
    unittest.main()
