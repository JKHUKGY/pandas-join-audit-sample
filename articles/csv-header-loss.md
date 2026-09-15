# Your CSV validator cannot see the value that already disappeared

By junzheng jia · September 15, 2026

I made a two-line CSV to test a question that is easy to miss in an import review: what information survives long enough for the validator to inspect it?

```csv
account_id,email,email
001,billing@example.test,other@example.test
```

Both addresses are invented. The duplicate column name is deliberate. Suppose the importer expects an account identifier and an email address, reads each row into a dictionary, then checks its keys. That looks like a reasonable order of operations. Here is what it misses:

```python
import csv
import io

text = "account_id,email,email\n001,billing@example.test,other@example.test\n"
record = next(csv.DictReader(io.StringIO(text), strict=True))
print(record)
print(set(record) == {"account_id", "email"})
```

On Python 3.13.9, I got:

```text
{'account_id': '001', 'email': 'other@example.test'}
True
```

The record has exactly the expected keys. It also has an email address that an ordinary format check could accept. The other address has disappeared from the returned dictionary. No validator that receives only that dictionary can establish that there used to be two competing values.

I would reject this file before creating any account records. Picking the last email silently turns a parsing detail into a decision about where an account's messages should go. Picking the first would be equally arbitrary.

## Parsing success does not resolve an ambiguous header

Setting `strict=True` does not reject this example. It asks the CSV parser to report bad CSV input; repeated header text is still parsable CSV. In the experiment, both columns exist in the parsed row. They collide when the row becomes a mapping with one value per key.

This is a useful distinction when reviewing an import: ask what a check establishes. Successful parsing establishes less than an unambiguous schema. A valid schema establishes less than a correct account-to-address relationship.

The [Python documentation](https://docs.python.org/3/library/csv.html#csv.DictReader) describes `DictReader` as mapping fields to dictionary keys. It also documents another behavior worth deciding explicitly: surplus fields go under `restkey`, which defaults to `None`; missing fields receive `restval`, also `None` by default. An application that selects only its known keys can overlook the surplus data. These defaults are useful mechanisms, but they are not my import policy.

## Check the representation that still contains the evidence

The small reader below checks the header and each row's width while they are still lists. Only then does it construct dictionaries.

```python
def read_checked(text):
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
```

The duplicate-header fixture now raises `ValueError: duplicate header`. A valid quoted comma remains part of its field. Quoted newlines work too: splitting the input on newline characters and then commas would not be an adequate substitute for the parser.

The error reports a logical record number, counting the header as record one. That can differ from a physical line number when a field spans lines. I avoid printing the whole offending record; an account import may contain information that does not belong in a log.

This reader checks exact header equality. It deliberately preserves `id` and ` id` as different names, and preserves `001` and `NA` as strings. If an importer trims or case-folds headers, it must check for collisions again after that transformation. “Clean up the names” can otherwise reintroduce the same information loss one step later.

## Choose what happens to incomplete records

I gave missing fields and empty values different outcomes:

| Input after the header `id,email` | Result |
| --- | --- |
| `001` | Reject: one field instead of two |
| `001,` | Accept structurally: the email is an empty string |
| `001,a@example.test,extra` | Reject: three fields instead of two |
| A blank record | Reject: zero fields |

An accepted empty string still needs a business rule. This reader does not decide whether an email is mandatory or whether a header is an allowed column name. It makes those later checks possible without first losing a column. A file containing only a valid header returns an empty list; whether an empty import is useful is another explicit decision.

I also return the list only after inspecting every record. A valid first row followed by an invalid second row raises an error without returning a partial result. That helps a caller separate validation from effects. It is not a database transaction: a caller that writes elsewhere before this function finishes needs its own rollback design.

## Reproduce the result, then set a larger contract

The [experiment](header_loss.py) and [tests](test_header_loss.py) use the Python standard library. With these files in the current directory, run:

```sh
python header_loss.py
python -m unittest -v test_header_loss
```

All ten tests passed on macOS with Python 3.13.9 on September 15, 2026. They cover the original silent overwrite, surplus and missing fields, explicit empty values, later-record failure, blank headers and records, quoted commas and newlines, exact text preservation, header-only input, and an unterminated quote. These are local synthetic experiments, not evidence from a customer system.

The implementation holds the input and result in memory. It is a teaching example, not an unrestricted upload endpoint. A deployed importer needs byte, field and record limits, a defined encoding and dialect, required-column checks, value validation, and a decision about committing accepted data. A streaming version also needs to decide whether earlier rows may escape before a later failure.

The review question I would keep is small: **does this conversion discard evidence that the next validation step needs?** For this file, moving one header check ahead of dictionary creation changes an apparently valid account record into an actionable rejection.
