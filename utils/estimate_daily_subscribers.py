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
    snap['timestamp'] = pd.to_datetime(snap['collected_at'])
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
    st.write("[DEBUG] preprocess -> full_snap sample:", full_snap.head())

    # 4) merge
    channel_daily = channel_daily.drop(columns=['subscriber_count'], errors='ignore')
    merged = channel_daily.merge(
        full_snap[['date', 'subscriber_count']],
        on='date', how='left'
    )
    st.write("[DEBUG] preprocess -> merged sample:", merged.head())
    return merged


def estimate_daily_subscribers(
    ch_snap: pd.DataFrame,
    spread_change_df: pd.DataFrame
) -> pd.DataFrame:
    """
    일별 구독자수를 추정하여 반환합니다.

    ch_snap: DataFrame with ['collected_at','subscriber_count']
      - subscriber_count는 만 단위로만 측정된 값
    spread_change_df: DataFrame with ['Date','Spread Change']
      - 일별 추정 구독자 증가량

    반환: DataFrame with ['Date','Estimated Subscribers']
    확실한 제약조건을 지키며, 단순합이 이를 벗어날 경우 보정치를 적용합니다.
    """
    # 1) ch_snap 전처리: 날짜 및 계단식 구독수 구간
    snap = ch_snap.copy()
    snap['Date'] = parse_published_at(snap['collected_at']).dt.date
    # 계단값: 만단위로 기록된 subscriber_count

    # 2) spread_change_df 전처리: 날짜 및 일별 변화량
    spread = spread_change_df.copy()
    spread['Date'] = pd.to_datetime(spread['Date']).dt.date
    spread = spread.set_index('Date')

    # 3) 날짜 인덱스 범위
    all_dates = pd.date_range(
        start=min(snap['Date'].min(), spread.index.min()),
        end=max(snap['Date'].max(), spread.index.max()),
        freq='D'
    ).date

    # 4) 초기 estimated Series 생성
    est = pd.Series(index=all_dates, dtype=float)

    # 5) snap에서 계단 제약: 각 측정일에만 known count
    known = snap.drop_duplicates('Date').set_index('Date')['subscriber_count']

    # 6) spread change에서 일별 증가량
    deltas = spread['Spread Change'].reindex(all_dates).fillna(0)

    # 7) 누적 적용하며 제약 검증
    prev_est = None
    for date in all_dates:
        if date in known.index:
            # 측정된 계단값
            lower = known.loc[date]
            upper = lower + 1  # 만단위, +1만 이하 구독자
            # 기본값 설정
            est.loc[date] = lower
            prev_est = est.loc[date]
        else:
            # spread 적용
            delta = deltas.loc[date]
            if prev_est is None:
                # 시작 전에 측정데이터가 없으면 0으로 시작
                prev_est = 0.0
            nominal = prev_est + delta
            # 제약조건: between 최근 lower and upper
            # 찾을 수 있는 가장 가까운 이전 known
            prev_known_date = known.index[known.index < date]
            if len(prev_known_date) > 0:
                base_date = prev_known_date.max()
                base = known.loc[base_date]
                low = base
                high = base + 1
                # 보정
                est.loc[date] = min(max(nominal, low), high)
            else:
                # 아직 첫 측정 전
                est.loc[date] = nominal if nominal >= 0 else 0
            prev_est = est.loc[date]

    # 8) 결과 DataFrame
    result = est.reset_index()
    result.columns = ['Date', 'Estimated Subscribers']
    return result


#---
# def aggregate_views_within_days(
#     df: pd.DataFrame,
#     days: int = 14
# ) -> pd.Series:
#     """
#     각 video_id별로 업로드 이후 최대 `days`일 이내의
#     조회수 변화량(view_end - view_start)을 계산하여 반환합니다.
#     """
#     df_copy = df.copy()
#     df_copy['published_at'] = parse_published_at(df_copy['published_at'])
#     df_copy['timestamp'] = parse_published_at(df_copy['timestamp'])

#     # 최초 스냅샷
#     first_snaps = (
#         df_copy[df_copy['timestamp'] >= df_copy['published_at']]
#         .sort_values(['video_id', 'timestamp'])
#         .groupby('video_id')
#         .first()
#     )

#     # 종료 스냅샷 선택
#     def pick_end_snap(group: pd.DataFrame) -> pd.Series:
#         pub_time = group['published_at'].iloc[0]
#         cutoff = pub_time + timedelta(days=days)
#         snaps_after = group[group['timestamp'] >= group['published_at']]

#         if snaps_after['timestamp'].max() >= cutoff:
#             return (
#                 snaps_after[snaps_after['timestamp'] >= cutoff]
#                 .sort_values('timestamp')
#                 .iloc[0]
#             )
#         return snaps_after.sort_values('timestamp').iloc[-1]

#     end_snaps = df_copy.groupby('video_id').apply(pick_end_snap, include_groups=False)
#     delta_views = end_snaps['view_count'] - first_snaps['view_count']
#     st.write("[DEBUG] aggregate_views -> sum delta_views:", float(delta_views.sum()))
#     return delta_views.rename('delta_views')


# def compute_channel_gain_index(
#     df: pd.DataFrame,
#     r0: float,
#     days: int = 14,
#     daily_avg: float = None
# ) -> float:
#     """
#     채널 수준의 GainIndex를 계산합니다.
#     """
#     df_sorted = df.sort_values('timestamp')
#     st.write("[DEBUG] channel_gain -> total snaps:", len(df_sorted))

#     # 구독자 변화량 ΔS
#     if daily_avg is not None:
#         delta_subs = daily_avg * days
#     else:
#         max_time = df_sorted['timestamp'].max()
#         start_time = max_time - timedelta(days=days)
#         recent = df_sorted[df_sorted['timestamp'] >= start_time]
#         st.write("[DEBUG] channel_gain -> recent snaps:", len(recent))
#         if len(recent) < 2:
#             st.write("[DEBUG] channel_gain -> insufficient snapshots")
#             return 0.0
#         delta_subs = recent['subscriber_count'].iloc[-1] - recent['subscriber_count'].iloc[0]
#     st.write("[DEBUG] channel_gain -> ΔS:", float(delta_subs))

#     # 조회수 변화량 합계
#     delta_views = aggregate_views_within_days(df_sorted, days)
#     total_views_d = delta_views.sum()
#     st.write("[DEBUG] channel_gain -> total_views_d:", float(total_views_d))

#     # 실제 전환율 r_d
#     actual_rate = delta_subs / total_views_d if total_views_d > 0 else 0.0
#     st.write("[DEBUG] channel_gain -> actual_rate:", float(actual_rate))
#     st.write("[DEBUG] channel_gain -> expected_rate:", float(r0))

#     # GainIndex 계산
#     gain_index = actual_rate / r0 if r0 > 0 else 0.0
#     st.write("[DEBUG] channel_gain -> gain_index:", float(gain_index))
#     return gain_index


# def compute_video_gain_scores(
#     channel_df: pd.DataFrame,
#     ch_snap: pd.DataFrame,
#     end_subs: int,
#     total_view: int,
#     c: float = 100.0,
#     days: int = 14
# ) -> pd.DataFrame:
#     """
#     1) preprocess_channel_data 호출
#     2) 영상별 Gain Score 계산
#     """
#     # 1) 전처리
#     merged_df = preprocess_channel_data(channel_df, ch_snap)

#     # 2) 롱폼 필터링 및 r0 계산
#     long_df = merged_df[merged_df['is_short'] == False].copy()
#     r0_baseline = (end_subs / total_view) / np.log(end_subs * 0.5 + c) if total_view > 0 else 0.0
#     st.write("[DEBUG] compute_video_gain -> r0_baseline:", float(r0_baseline))

#     # 3) GainIndex
#     gain_index = compute_channel_gain_index(
#         df=long_df,
#         r0=r0_baseline,
#         days=days
#     )
    
#     # 4) 영상별 조회수 변화량 및 가중치
#     delta_views = aggregate_views_within_days(long_df, days)
#     total_views_long = delta_views.sum()
#     weights = delta_views / total_views_long if total_views_long > 0 else pd.Series(0, index=delta_views.index)
#     st.write("[DEBUG] compute_video_gain -> weights:", weights.head())

#     # 5) Gain Score
#     gain_scores = gain_index * weights
#     st.write("[DEBUG] compute_video_gain -> gain_scores:", gain_scores.head())

#     # 6) 결과 반환
#     videos = channel_df[['video_id', 'is_short']].drop_duplicates('video_id')
#     result = videos.copy()
#     result['gain_score'] = result['video_id'].map(gain_scores.to_dict())
#     result.loc[result['is_short'], 'gain_score'] = None
#     st.write("[DEBUG] compute_video_gain -> result sample:", result.head())
    
#     return result[['video_id', 'gain_score']]