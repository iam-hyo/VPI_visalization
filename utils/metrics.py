# utils/metrics.py
from datetime import datetime, timedelta
import pandas as pd

def get_subscriber_metrics(df: pd.DataFrame, days: int = 10):
    df = df.sort_values('timestamp')
    cutoff = df['timestamp'].max() - timedelta(days=days)
    recent = df[df['timestamp'] >= cutoff]
    if len(recent) < 2:
        return 0.0, 0
    start, end = recent['subscriber_count'].iloc[0], recent['subscriber_count'].iloc[-1]
    growth = (end - start) / start if start else 0.0
    daily_avg = (end - start) / (len(recent) - 1)
    return growth, daily_avg

def filter_shorts(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['is_short'] == True]

def filter_longforms(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['is_short'] == False]

def avg_views(df: pd.DataFrame, days: int = 10, is_short: bool = None) -> float:
    cutoff = df['published_at'].max() - timedelta(days=days)
    recent = df[df['published_at'] >= cutoff]
    if is_short is True:
        recent = filter_shorts(recent)
    elif is_short is False:
        recent = filter_longforms(recent)
    return float(recent['view_count'].mean()) if not recent.empty else 0.0

def moving_average_views(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    df = df.sort_values('published_at').copy()
    df['ma_view_count'] = df['view_count'].rolling(window, min_periods=1).mean()
    return df[['published_at', 'ma_view_count']]

def calculate_contribution(df: pd.DataFrame) -> pd.DataFrame:
    total = df['view_count'].sum()
    df = df.copy()
    df['contribution'] = df['view_count'] / total if total else 0
    return df[['video_id', 'contribution']]

def video_contribution_by_type(df: pd.DataFrame) -> pd.DataFrame:
    shorts = calculate_contribution(filter_shorts(df)).assign(type='Shorts')
    longs  = calculate_contribution(filter_longforms(df)).assign(type='Long')
    return pd.concat([shorts, longs], ignore_index=True)

def get_recent_videos(df: pd.DataFrame, days: int = 10) -> pd.DataFrame:
    cutoff = datetime.now() - timedelta(days=days)
    return df[df['published_at'] >= cutoff]
