"""An executable pandas join example using invented sensor data."""
from io import StringIO
import json
import pandas as pd


def read_example(text):
    """Keep identifiers literal; this example does not infer missing markers."""
    return pd.read_csv(StringIO(text), dtype="string", keep_default_na=False)


def audited_left_join(observations, lookup, key):
    """Require one lookup record per key; retain unmatched observations.

    Blank/null keys are rejected. Nonblank key text is compared exactly. The
    returned _merge column reports match status; callers decide what to do with
    unmatched rows. Inputs are not modified.
    """
    for name, frame in (("observations", observations), ("lookup", lookup)):
        if not frame.columns.is_unique:
            raise ValueError(f"{name} has duplicate column names")
        if key not in frame.columns:
            raise ValueError(f"{name} is missing key column {key!r}")
        if "_merge" in frame.columns:
            raise ValueError("_merge is reserved for the match report")
        values = frame[key]
        if values.isna().any() or values.astype("string").str.strip().eq("").any():
            raise ValueError(f"{name} contains null or blank keys")

    result = observations.merge(
        lookup, on=key, how="left", validate="many_to_one",
        indicator=True, sort=False,
    )
    if len(result) != len(observations):
        raise RuntimeError("left join changed the observation count")
    return result


def demo():
    observations = read_example(
        "reading_id,sensor_id,value\n"
        "r1,001,10\nr2,001,11\nr3,002,12\nr4,999,13\n"
    )
    conflicting = read_example(
        "sensor_id,room\n001,north\n001,south\n002,lab\n"
    )
    naive = observations.merge(conflicting, on="sensor_id", how="left")
    rejected = False
    try:
        audited_left_join(observations, conflicting, "sensor_id")
    except pd.errors.MergeError:
        rejected = True

    # A separate, explicitly chosen example lookup. No automatic deduplication.
    resolved = read_example("sensor_id,room\n001,north\n002,lab\n")
    checked = audited_left_join(observations, resolved, "sensor_id")
    return {
        "pandas_version": pd.__version__,
        "input_rows": len(observations),
        "naive_output_rows": len(naive),
        "duplicate_lookup_rejected": rejected,
        "checked_output_rows": len(checked),
        "unmatched_reading_ids": checked.loc[
            checked["_merge"].eq("left_only"), "reading_id"
        ].tolist(),
        "checked_sensor_ids": checked["sensor_id"].tolist(),
    }


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
