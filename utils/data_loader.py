import pandas as pd

def load_data(source="csv"):
    if source == "csv":
        return pd.read_csv("data/processed_data.csv", parse_dates=["timestamp"])
    elif source == "json":
        return pd.read_json("data/raw_data.json")
    else:
        raise ValueError("지원하지 않는 데이터 소스입니다.")
