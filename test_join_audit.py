import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from join_audit import audited_left_join, read_example, demo


class JoinTests(unittest.TestCase):
    def test_demo_exposes_inflation_then_retains_unknown_row(self):
        result = demo()
        self.assertEqual(result["input_rows"], 4)
        self.assertEqual(result["naive_output_rows"], 6)
        self.assertTrue(result["duplicate_lookup_rejected"])
        self.assertEqual(result["checked_output_rows"], 4)
        self.assertEqual(result["unmatched_reading_ids"], ["r4"])

    def test_repeated_observations_and_order_are_preserved(self):
        left = read_example("id,key\nb,002\na,001\nc,001\n")
        right = read_example("key,label\n001,one\n002,two\n")
        original_left, original_right = left.copy(deep=True), right.copy(deep=True)
        result = audited_left_join(left, right, "key")
        self.assertEqual(result["id"].tolist(), ["b", "a", "c"])
        self.assertEqual(result["label"].tolist(), ["two", "one", "one"])
        assert_frame_equal(left, original_left)
        assert_frame_equal(right, original_right)

    def test_even_identical_duplicate_lookup_rows_are_rejected(self):
        with self.assertRaises(pd.errors.MergeError):
            audited_left_join(read_example("key\n001\n"),
                              read_example("key,label\n001,x\n001,x\n"), "key")

    def test_literal_na_and_leading_zeros_are_not_coerced(self):
        left = read_example("key,id\nNA,a\n001,b\n1,c\n")
        right = read_example("key,label\nNA,not-an-empty-key\n001,zero-prefix\n")
        result = audited_left_join(left, right, "key")
        self.assertEqual(result["key"].tolist(), ["NA", "001", "1"])
        self.assertEqual(result["_merge"].astype("string").tolist(),
                         ["both", "both", "left_only"])

    def test_null_and_blank_keys_are_rejected_on_either_side(self):
        for bad in (None, pd.NA, "", " \t"):
            for side in (0, 1):
                with self.subTest(bad=repr(bad), side=side):
                    frames = [pd.DataFrame({"key": ["001"]}),
                              pd.DataFrame({"key": ["001"]})]
                    frames[side].loc[0, "key"] = bad
                    with self.assertRaisesRegex(ValueError, "null or blank"):
                        audited_left_join(*frames, "key")

    def test_nonblank_whitespace_is_not_silently_normalized(self):
        result = audited_left_join(read_example("key,id\n 001,a\n"),
                                   read_example("key,label\n001,x\n"), "key")
        self.assertEqual(result.loc[0, "key"], " 001")
        self.assertEqual(result.loc[0, "_merge"], "left_only")

    def test_empty_lookup_preserves_all_observations(self):
        result = audited_left_join(read_example("key\n001\n002\n"),
                                   read_example("key,label\n"), "key")
        self.assertEqual(len(result), 2)
        self.assertTrue(result["_merge"].eq("left_only").all())

    def test_ambiguous_schema_is_rejected(self):
        valid = read_example("key,label\n001,x\n")
        invalid = [pd.DataFrame([["001", "001"]], columns=["key", "key"]),
                   pd.DataFrame({"other": ["001"]}),
                   pd.DataFrame({"key": ["001"], "_merge": ["old"]})]
        for bad in invalid:
            for left, right in ((bad, valid), (valid, bad)):
                with self.assertRaises(ValueError):
                    audited_left_join(left, right, "key")


if __name__ == "__main__":
    unittest.main()
