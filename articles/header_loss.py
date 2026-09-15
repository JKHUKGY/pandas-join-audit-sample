"""Small, in-memory CSV experiment accompanying csv-header-loss.md."""

import csv
import io
import json


def read_checked(text):
    """Return all records only after checking exact header names and row widths."""
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    header = next(reader, None)
    if not header or any(not name.strip() for name in header):
        raise ValueError("missing or blank header")
    if len(header) != len(set(header)):
        raise ValueError("duplicate header")

    result = []
    for record_number, fields in enumerate(reader, start=2):
        if len(fields) != len(header):
            raise ValueError(
                f"record {record_number}: expected {len(header)} fields, "
                f"got {len(fields)}"
            )
        result.append(dict(zip(header, fields, strict=True)))
    return result


def demo():
    text = "account_id,email,email\n001,billing@example.test,other@example.test\n"
    ordinary = next(csv.DictReader(io.StringIO(text), strict=True))
    try:
        read_checked(text)
    except ValueError as exc:
        rejection = str(exc)
    else:
        raise AssertionError("the ambiguous header was accepted")
    return {
        "ordinary_record": ordinary,
        "expected_keys_check_passes": set(ordinary) == {"account_id", "email"},
        "checked_reader_error": rejection,
        "valid_record": read_checked(
            'account_id,email,note\n001,billing@example.test,"renewal, annual"\n'
        )[0],
    }


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
