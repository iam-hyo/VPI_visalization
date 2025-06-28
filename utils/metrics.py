# utils/metrics.py
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Union
import streamlit as st

def parse_published_at(series: pd.Series) -> pd.Series:
    """
    Mixed-format datetime strings → naive datetime in Asia/Seoul.

    Supports two input formats in `series`:
      1) ISO8601 with Z:   "2025-06-21T10:00:50Z"
      2) Simple local:     "2025-06-20 17:00"

    Returns
    -------
    pd.Series of dtype datetime64[ns], with all times in Asia/Seoul (naive).
    """
    s = series.astype(str)

    # 1) ISO8601(Z) 끝나는 항목과 아닌 항목 분리
    mask_iso = s.str.endswith('Z')

    # 2) ISO8601 → UTC-aware → Asia/Seoul → tz-naive
    dt_iso = (
        pd.to_datetime(s[mask_iso], utc=True, errors='coerce')
          .dt.tz_convert('Asia/Seoul')
          .dt.tz_localize(None)
    )

    # 3) Simple format → naive (assume already Asia/Seoul)
    dt_simple = pd.to_datetime(
        s[~mask_iso], 
        format='%Y-%m-%d %H:%M', 
        errors='coerce'
    )

    # 4) 두 결과 합치기
    result = pd.Series(index=s.index, dtype='datetime64[ns]')
    result[mask_iso]     = dt_iso
    result[~mask_iso]    = dt_simple

    # 5) NaT 검사 (선택)  
    if result.isna().any():
        missing = series[result.isna()].unique().tolist()
        import streamlit as st
        st.warning(f"⚠️ parse_published_at()에서 NaT 발생: {missing}")

    return result

def format_korean_count(n: int) -> str:
    """
    1억 단위(100,000,000)와 만 단위(10,000)로 끊어서 
    '몇억 몇만' 형태로 반환합니다.
    ex) 2830000 → '283만'
        123456789 → '1억 2345만'
        100000000 → '1억'
        999 → '999'
    """
    parts = []
    # 1억 단위
    if n >= 100_000_000:
        eok = n // 100_000_000
        parts.append(f"{eok}억")
        n %= 100_000_000
    # 만 단위
    if n >= 10_000:
        man = n // 10_000
        parts.append(f"{man}만")
        n %= 10_000
    # 나머지(1만 미만)는 생략하거나, 필요하면 표시
    # if n > 0:
    #     parts.append(f"{n:,}")
    if not parts:
        # 만 미만(1~9999)은 그냥 천단위 콤마 표기
        return f"{n:,}"
    return " ".join(parts)

def get_subscriber_metrics(df: pd.DataFrame, days: int = 10): #10일 이내 구독자 변동성장률 가져옴
    df = df.sort_values('timestamp') 
    cutoff = df['timestamp'].max() - timedelta(days=days) #최근 {days}일 전 timestamp
    recent = df[df['timestamp'] >= cutoff]

    if len(recent) < 2:
        return 0.0, 0.0, 0, 0
    first, start, end = df['subscriber_count'].iloc[0], recent['subscriber_count'].iloc[0], recent['subscriber_count'].iloc[-1]
    
    actual_days = (recent['timestamp'].iloc[-1] - recent['timestamp'].iloc[0]).total_seconds() / (3600 * 24)
    growth = (end - first) # 수집기간 중 구독자 변화량
    daily_avg = (end - start) / actual_days if actual_days > 0 else 0 # recent기간중 일일 변화량
    return growth, daily_avg, end, start

def filter_shorts(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['is_short'] == True]

def filter_longforms(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['is_short'] == False]

def avg_view_by_days_since_published(
    df: pd.DataFrame,
    max_days: int = 10,
    is_short: bool = None
) -> pd.DataFrame:
    """
    공개 후 1일부터 max_days일까지,
    (video_id, day)별로 snapshot 평균 view_count를 구한 뒤
    day별로 영상 평균을 다시 계산해 리턴합니다.
    """

    df = df.copy()

    # 3) 1 <= day <= max_days 필터
    df = df[(df['day_since_pub'] >= 1) & (df['day_since_pub'] <= max_days)]

    # 4) 숏/롱폼 필터링
    if is_short is True:
        df = df[df['is_short'] == True]
    elif is_short is False:
        df = df[df['is_short'] == False]

    # 6) (video_id, day)별 snapshot 평균
    grp1 = (
        df
        .groupby(['video_id', 'day_since_pub'], as_index=False)
        ['view_count']
        .mean()
        .rename(columns={'view_count': 'video_day_avg'})
    )

    # 7) day별 영상 평균
    grp2 = (
        grp1
        .groupby('day_since_pub', as_index=False)
        ['video_day_avg'].mean()
        .rename(columns={'day_since_pub': 'day', 'video_day_avg': 'avg_view_count'})
    )

    # all_days 생성 & merge
    all_days = pd.DataFrame({'day': range(1, max_days+1)})
    result = all_days.merge(grp2, on='day', how='left')

    # 누락값 보간 & 앞뒤 채우기
    result['avg_view_count'] = (
    result['avg_view_count']
        .interpolate(method='linear')
        .bfill()
        .ffill()
        .fillna(0)
        .round(0)
        .astype(int)
    )

    arr = result['avg_view_count']
    result['avg_view_count'] = arr.round(0).astype(int)

    # pivot & 컬럼명 변경
    pivot = result.set_index('day')['avg_view_count'].to_frame().T
    pivot.columns = [f"{d}일차" for d in result['day']]
    pivot.index = ['평균조회수']

    return pivot, result

def avg_views(df: pd.DataFrame, days: int = 10, is_short: bool = None) -> float: #10일 이내 평균조회수 계산하는 함수
    df = df.copy()
    df['published_at_dt'] = parse_published_at(df['published_at'])

    latest_time = df['published_at_dt'].max()
    cutoff = latest_time - timedelta(days=days)
    recent = df[df['published_at_dt'] >= cutoff] 
    if is_short is True:
        recent = filter_shorts(recent)
    elif is_short is False:
        recent = filter_longforms(recent)
    return float(recent['view_count'].mean()) if not recent.empty else 0.0

def get_recent_videos(df: pd.DataFrame, days: int = 10) -> pd.DataFrame: #최근 10일 이내 함수 걷어내는 함수
    cutoff = datetime.now() - timedelta(days=days)
    # cutoff.dt.tz_localize(None)
    df = df.copy()
    publish_date = pd.to_datetime(df['published_at'], utc=True, errors='coerce')
    df['published_at'] = publish_date.dt.tz_localize(None)
    return df[df['published_at'] >= cutoff]
