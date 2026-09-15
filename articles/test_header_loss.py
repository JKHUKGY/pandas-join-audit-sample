import csv
import io
import unittest

from header_loss import demo, read_checked


class HeaderLossTests(unittest.TestCase):
    def test_duplicate_header_loses_value_before_key_validation(self):
        report = demo()
        self.assertEqual(report["ordinary_record"], {
            "account_id": "001", "email": "other@example.test"
        })
        self.assertTrue(report["expected_keys_check_passes"])
        self.assertEqual(report["checked_reader_error"], "duplicate header")

    def test_extra_field_is_retained_under_none_by_dictreader(self):
        row = next(csv.DictReader(io.StringIO("id,email\n001,a@example.test,extra\n")))
        self.assertEqual(row[None], ["extra"])
        with self.assertRaisesRegex(ValueError, "expected 2 fields, got 3"):
            read_checked("id,email\n001,a@example.test,extra\n")

    def test_missing_field_rejected_but_explicit_empty_is_valid(self):
        with self.assertRaisesRegex(ValueError, "expected 2 fields, got 1"):
            read_checked("id,email\n001\n")
        self.assertEqual(read_checked("id,email\n001,\n"), [{"id": "001", "email": ""}])

    def test_no_partial_result_when_later_record_is_invalid(self):
        with self.assertRaisesRegex(ValueError, "record 3"):
            read_checked("id,email\n001,a@example.test\n002\n")

    def test_empty_or_blank_headers_rejected(self):
        for text in ("", "\n", "id,\n001,a\n", "id, \n001,a\n"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "header"):
                read_checked(text)

    def test_blank_record_rejected(self):
        with self.assertRaisesRegex(ValueError, "got 0"):
            read_checked("id,email\n\n")

    def test_quoted_comma_multiline_and_crlf_preserved(self):
        self.assertEqual(read_checked('id,note\r\n001,"first, line\r\nsecond"\r\n'),
                         [{"id": "001", "note": "first, line\r\nsecond"}])

    def test_header_and_values_are_not_normalized(self):
        self.assertEqual(read_checked("id, id,code\n001, 001,NA\n"),
                         [{"id": "001", " id": " 001", "code": "NA"}])

    def test_header_only_file_is_valid_empty_data(self):
        self.assertEqual(read_checked("id,email\n"), [])

    def test_unterminated_quote_raises_parser_error(self):
        with self.assertRaises(csv.Error):
            read_checked('id,note\n001,"unfinished\n')


if __name__ == "__main__":
    unittest.main()
