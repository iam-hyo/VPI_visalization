"""
video_gain.py with separated preprocessing function

이 파일은 크게 4개의 함수로 구성되어 있습니다:
1) preprocess_channel_data: channel_df와 ch_snap을 날짜 기준으로 병합하고 전처리
2) aggregate_views_within_days: 영상별 조회수 변화량 집계
3) compute_channel_gain_index: 채널 수준 GainIndex 계산
4) compute_video_gain_scores: 전처리된 데이터를 이용해 영상별 Gain Score 계산

호출 예시:
```python
from video_gain import compute_video_gain_scores

video_gain_df = compute_video_gain_scores(
    channel_df=ch_df,
    ch_snap=ch_snap,
    end_subs=latest_subs,
    total_view=total_view,
    c=100.0,
    days=14
)
```
"""
import numpy as np
import pandas as pd
import streamlit as st
from datetime import timedelta
from utils.metrics import parse_published_at


def preprocess_channel_data(
    channel_df: pd.DataFrame,
    ch_snap: pd.DataFrame
) -> pd.DataFrame:
    """
    channel_df와 ch_snap을 날짜 기준으로 병합하여 subscriber_count를 업데이트합니다.
    1) channel_df: timestamp→datetime, date 추출, video_id+date별 첫 row만 남김
    2) ch_snap: collected_at→datetime, date 추출, 날짜별 subscriber_count 정리
    3) 전체 날짜 기간을 보장하고 결측값은 전후일 구독자 수로 보간
    4) channel_daily에 subscriber_count merge
    """
    # 1) channel_df 전처리
    df = channel_df.copy()
    df['timestamp'] = parse_published_at(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    channel_daily = (
        df
        .sort_values('timestamp')
        .drop_duplicates(subset=['video_id', 'date'], keep='first')
    )

    # 2) ch_snap 전처리
    snap = ch_snap.copy()
    snap['timestamp'] = parse_published_at(snap['collected_at'])
    snap['date'] = snap['timestamp'].dt.date
    daily_snap = (
        snap[['date', 'subscriber_count']]
        .drop_duplicates('date')
        .sort_values('date')
    )

    # 3) 전체 날짜 보장 & 보간
    all_dates = pd.date_range(
        start=daily_snap['date'].min(),
        end=daily_snap['date'].max(),
        freq='D'
    ).date
    full_snap = (
        pd.DataFrame({'date': all_dates})
        .merge(daily_snap, on='date', how='left')
    )
    full_snap['subscriber_count'] = full_snap['subscriber_count'].interpolate()
    # st.write("[DEBUG] preprocess -> full_snap sample:", full_snap.head())

    # 4) merge
    channel_daily = channel_daily.drop(columns=['subscriber_count'], errors='ignore')
    merged = channel_daily.merge(
        full_snap[['date', 'subscriber_count']],
        on='date', how='left'
    )
    # st.write("[DEBUG] preprocess -> merged sample:", merged.head())
    return merged


def aggregate_views_within_days(
    df: pd.DataFrame,
    days: int = 14
) -> pd.Series:
    """
    각 video_id별로 업로드 이후 최대 `days`일 이내의
    조회수 변화량(view_end - view_start)을 계산하여 반환합니다.
    """
    df_copy = df.copy()
    df_copy['published_at'] = parse_published_at(df_copy['published_at'])
    df_copy['timestamp'] = parse_published_at(df_copy['timestamp'])

    # 최초 스냅샷
    first_snaps = (
        df_copy[df_copy['timestamp'] >= df_copy['published_at']]
        .sort_values(['video_id', 'timestamp'])
        .groupby('video_id')
        .first() # 그룹 별 첫번재 row 선택
    )

    # 종료 스냅샷 선택
    def pick_end_snap(group: pd.DataFrame) -> pd.Series:
        pub_time = group['published_at'].iloc[0]        # 업로드 일자
        cutoff = pub_time + timedelta(days=days)
        snaps_after = group[group['timestamp'] >= group['published_at']]

        if snaps_after['timestamp'].max() >= cutoff:
            return (
                snaps_after[snaps_after['timestamp'] >= cutoff]
                .sort_values('timestamp')
                .iloc[0]
            )
        return snaps_after.sort_values('timestamp').iloc[-1]

    end_snaps = df_copy.groupby('video_id').apply(pick_end_snap, include_groups=False)
    delta_views = end_snaps['view_count'] - first_snaps['view_count']       # 조회수 변화량 계산
    # st.write("[DEBUG] aggregate_views -> sum delta_views:", float(delta_views.sum()))
    return delta_views.rename('delta_views')


def compute_channel_gain_index(
    ch_long_df: pd.DataFrame,
    r0: float,
    days: int = 14,
    daily_avg: float = None,
    estimated_daily_subscribers: pd.DataFrame = None
) -> float:
    """
    채널 수준의 GainIndex를 계산합니다.
    """
    df_sorted = ch_long_df.sort_values('timestamp')
    # st.write("[DEBUG] channel_gain -> total snaps:", len(df_sorted))

   # 2) ΔS (구독자 변화량) 계산
    if estimated_daily_subscribers is not None:
        # Date 컬럼을 datetime으로 변환
        est = estimated_daily_subscribers.copy()
        est['Date'] = pd.to_datetime(est['Date'])
        # 분석 기간의 끝과 시작 구하기
        max_time = df_sorted['timestamp'].max().normalize()
        start_time = (max_time - timedelta(days=days)).normalize()
        # 해당 기간에 해당하는 일자 필터링
        mask = (est['Date'] >= start_time) & (est['Date'] <= max_time)
        recent_est = est.loc[mask, 'Estimated Subscribers']
        if recent_est.empty:
            return 0.0
        delta_subs = recent_est.sum()

    else:
        # 원본 스냅샷으로부터 직접 계산
        max_time = df_sorted['timestamp'].max()
        start_time = max_time - timedelta(days=days)
        recent = df_sorted[df_sorted['timestamp'] >= start_time]
        if len(recent) < 2:
            return 0.0
        delta_subs = recent['subscriber_count'].iloc[-1] - recent['subscriber_count'].iloc[0]

    # 조회수 변화량 합계
    delta_views = aggregate_views_within_days(df_sorted, days)
    total_views_d = delta_views.sum()
    # st.write("[DEBUG] channel_gain -> total_views_d:", float(total_views_d))

    # 실제 전환율 r_d
    actual_rate = delta_subs / total_views_d if total_views_d > 0 else 0.0

    # GainIndex 계산
    gain_index = actual_rate / r0 if r0 > 0 else 0.0
    # st.write("[DEBUG] channel_gain -> actual_rate:", float(actual_rate))
    # st.write("[DEBUG] channel_gain -> expected_rate:", float(r0))
    # st.write("[DEBUG] channel_gain -> gain_index:", float(gain_index))
    return gain_index


def compute_video_gain_scores(
    channel_df: pd.DataFrame,
    ch_snap: pd.DataFrame,
    estimated_daily_subscribers: pd.DataFrame,
    end_subs: int,
    total_view: int,
    c: float = 100.0,
    days: int = 14
) -> pd.DataFrame:
    """
    1) preprocess_channel_data 호출
    2) 영상별 Gain Score 계산
    """
    # 1) channel_df와 ch_snap을 날짜 기준으로 병합하여 subscriber_count를 업데이트.
    ch_df = preprocess_channel_data(channel_df, ch_snap)

    # 2) 롱폼 필터링 및 r0 계산
    ch_long_df = ch_df[ch_df['is_short'] == False].copy()
    r0_baseline = (end_subs / total_view) if total_view > 0 else 0.0
    # st.write("[DEBUG] compute_video_gain -> r0_baseline:", float(r0_baseline))

    # 3) GainIndex
    gain_index = compute_channel_gain_index(
        ch_long_df=ch_long_df,
        r0=r0_baseline,
        days=days,
        estimated_daily_subscribers=estimated_daily_subscribers
    )


    
    # 4) 영상별 조회수 변화량 및 가중치
    delta_views = aggregate_views_within_days(ch_long_df, days)
    total_views_long = delta_views.sum()
    weights = delta_views / total_views_long if total_views_long > 0 else pd.Series(0, index=delta_views.index)
    # st.write("[DEBUG] compute_video_gain -> weights:", weights.head())

    # 5) Gain Score
    gain_scores = gain_index * weights
    # st.write("[DEBUG] compute_video_gain -> gain_scores:", gain_scores.head())

    # 6) 결과 반환
    videos = channel_df[['video_id', 'is_short']].drop_duplicates('video_id')
    result = videos.copy()
    result['gain_score'] = result['video_id'].map(gain_scores.to_dict())
    # st.dataframe(result, use_container_width=True)
    filtered_gain = result.loc[result['gain_score'] > 0, 'gain_score']
    mean_gain = filtered_gain.mean() + 0.1 if not filtered_gain.empty else 1  # fallback: 그냥 1
    result['gain_score'] = result['gain_score'] / mean_gain + 0.1
    result.loc[result['is_short'], 'gain_score'] = None
    # st.write("[DEBUG] compute_video_gain -> result sample:", result.head())
    return result[['video_id', 'gain_score']]
