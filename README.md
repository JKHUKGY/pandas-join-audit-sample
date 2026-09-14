# Check a pandas join before trusting its row count

By junzheng jia. An original, executable writing sample using invented sensor
readings. This is a local demonstration, not a customer deployment or a completed
Saturn Cloud integration.

Four readings enter a left join. Six rows come out. Nothing crashes, and a later
aggregation can quietly count some readings twice.

The example in `join_audit.py` makes this happen deliberately. Sensor `001` has
two readings, but the lookup table also gives that sensor two conflicting rooms:
`north` and `south`. Each reading matches both lookup rows. The two readings
become four, while the other two input readings each produce one row.

## Define what one row means

Here, one observation row means one sensor reading. The lookup is supposed to
describe each sensor once. Several observations may use the same sensor, so
requiring unique keys on both sides would reject valid data. The required
relationship is **many observations to one lookup record**.

Pandas provides the check at the join itself:

```python
result = observations.merge(
    lookup,
    on="sensor_id",
    how="left",
    validate="many_to_one",
    indicator=True,
    sort=False,
)
```

With the conflicting lookup, `validate` raises `pandas.errors.MergeError`.
Even two identical lookup rows are rejected. This sample does not pick the first
one, delete rows, or guess which room is correct. Those are decisions about the
data source. The corrected lookup in the demo is a separately specified fixture,
not an automatic repair.

## Keep the records that do not match

Uniqueness does not establish completeness. Reading `r4` refers to sensor `999`,
which is absent from the corrected lookup. An inner join would drop that reading.
The left join retains it, and `indicator=True` marks it as `left_only` in the
`_merge` column. The example reports its reading ID for investigation. It does not
silently exclude it from a report or invent a room.

The explicit row-count check provides a second visible condition: after this
many-to-one left join, the output must contain as many rows as the observations.
It is useful, but insufficient alone. Four rows with the wrong sensor mappings
would still pass it. Tests therefore check identities, match status and order as
well as counts.

## Decide how identifiers and missing values behave

The tiny CSV fixtures use `dtype="string", keep_default_na=False`. That keeps
`001` distinct from `1` and preserves the literal key `NA`. This is an explicit
input policy for this example; it does not mean every real dataset should treat
`NA` as an identifier.

Null and blank keys are rejected before merging. Pandas can match null keys to
other null keys, so leaving them in this lookup could create a relationship the
data never established. Whitespace-only keys are also rejected. Nonblank text is
compared exactly: ` 001` is not silently trimmed into `001`. If normalization is
needed, specify and audit it before the join.

All fixture columns are loaded as strings. Numeric readings are not aggregated
here; a real analysis should separately validate and convert its measurement
columns. Key checks do not prove correct units, calibration, timestamps or
scientific conclusions.

## Run the sample

Tested on macOS with Python 3.13.9 and pandas 2.3.3 on September 14, 2026.
From a folder containing the three files:

```sh
python -m venv .venv
.venv/bin/python -m pip install pandas==2.3.3
.venv/bin/python join_audit.py
.venv/bin/python -m unittest -v test_join_audit
```

The recorded demo result is:

```json
{
  "pandas_version": "2.3.3",
  "input_rows": 4,
  "naive_output_rows": 6,
  "duplicate_lookup_rejected": true,
  "checked_output_rows": 4,
  "unmatched_reading_ids": ["r4"],
  "checked_sensor_ids": ["001", "001", "002", "999"]
}
```

All eight tests pass. They exercise the actual pandas merge, including repeated
observations, duplicate lookup rows, missing matches, empty lookups, literal
identifiers, blank/null keys, schema ambiguity and unchanged input frames.

The helper is intentionally limited to one key column and in-memory DataFrames.
It does not export files, modify a database or contact a service. Larger datasets,
composite keys and data-source correction require an explicit extension of this
contract. No Saturn Cloud runtime has been tested.

## Primary references

- [pandas merge: cardinality validation, indicators and null-key behavior](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html)
- [pandas read_csv: dtype and missing-value parsing](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)
