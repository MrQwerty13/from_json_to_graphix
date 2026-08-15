import os
import json
from typing import Any, Tuple
import pandas as pd


def format_for_analytics(data: Any, output_dir: str) -> Tuple[str, str, pd.DataFrame]:
    os.makedirs(output_dir, exist_ok=True)

    records = data
    if isinstance(data, dict):
        first_lists = [v for v in data.values() if isinstance(v, list)]
        if len(first_lists) == 1:
            records = first_lists[0]
        else:
            records = [data]

    try:
        df = pd.json_normalize(records)
    except Exception:
        df = pd.DataFrame(records)

    csv_path = os.path.join(output_dir, "formatted.csv")
    pretty_json_path = os.path.join(output_dir, "formatted.json")

    df.to_csv(csv_path, index=False)
    with open(pretty_json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return csv_path, pretty_json_path, df
