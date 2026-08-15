import os
import json
from typing import Any, Tuple
import pandas as pd


def format_for_analytics(data: Any, output_dir: str) -> Tuple[str, str, pd.DataFrame]:
    """Normalize JSON into a flat table and write CSV and pretty JSON.

    Args:
        data: JSON-parsed object (list or dict).
        output_dir: Directory to write formatted files into.

    Returns:
        Tuple of (csv_path, pretty_json_path, dataframe)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Ensure we have a list of records
    records = data
    if isinstance(data, dict):
        # If top-level keys map to lists, try to pick the first list
        # otherwise wrap dict in a list
        first_lists = [v for v in data.values() if isinstance(v, list)]
        if len(first_lists) == 1:
            records = first_lists[0]
        else:
            records = [data]

    # Use pandas.json_normalize to flatten
    try:
        df = pd.json_normalize(records)
    except Exception:
        # fallback: convert records to DataFrame directly
        df = pd.DataFrame(records)

    csv_path = os.path.join(output_dir, "formatted.csv")
    pretty_json_path = os.path.join(output_dir, "formatted.json")

    df.to_csv(csv_path, index=False)
    with open(pretty_json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return csv_path, pretty_json_path, df
