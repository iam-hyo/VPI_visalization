from datetime import timedelta
import numpy as np
import pandas as pd
import streamlit as st
from utils.metrics import parse_published_at

def compute_channel_gain_index( # days일 내 체널 기여도 계산
    channel_df: pd.DataFrame,
    r0: float = 0.01,
    c: float = 100.0,
    days: int = 10
) -> float:
    """
    채널 전체의 보정 전환 기여도 (GainIndex_chan) 계산.
    - channel_df: 해당 채널의 전체 시계열 데이터 (timestamp, published_at, view_count, subscriber_count 등 포함)
    - r0: 기준 전환율
    - c: 로그 안정화 상수
    - days: 계산 기준 기간 (일)
    """
    # 1) 최신 스냅샷 기준 누적 구독자 수
    end_subs = channel_df['subscriber_count'].iloc[-1]  # df는 timestamp 오름차순 정렬 전제

    # 2) 기간별 영상별 조회수 변화량 집계
    views_series = aggregate_views_within_days(channel_df, days=days)

    # 3) 채널 총 조회수
    total_views = views_series.sum()

    # 4) 기대 전환율: r0 / log(end_subs + c)
    expected_rate = r0 / np.log(end_subs + c)

    # 5) 실제 전환율: end_subs / total_views
    actual_rate = end_subs / total_views if total_views > 0 else 0.0

    # 6) 채널 GainIndex
    return actual_rate / expected_rate


def aggregate_views_within_days( #조회수 변화량을 영상별로 집계 (10일 경과 시점 고정)
    channel_df: pd.DataFrame,
    days: int = 10
) -> pd.Series:
    """
    업로드일로부터 최대 'days'일 이내의 조회수 변화량을
    video_id별로 계산해 반환.
    - 10일 초과 영상: published_at + days 시점 스냅샷을 고정 사용
    - 최근 영상(10일 미만): 최신 스냅샷 사용
    """
    df = channel_df.copy()
    # datetime 타입 보장
    df['published_at'] = parse_published_at(df['published_at'])
    df['timestamp']    = pd.to_datetime(df['timestamp'])

    # 1) 각 영상의 업로드 직후 초기 스냅샷(view0)
    first_snaps = (
        df[df['timestamp'] >= df['published_at']]
        .sort_values(['video_id', 'timestamp'])
        .groupby('video_id')
        .first()
    )

    # 2) 각 영상의 종료 스냅샷(view_end)
    def pick_end_snap(group: pd.DataFrame) -> pd.Series:
        pub = group['published_at'].iloc[0]
        cutoff = pub + timedelta(days=days)

        # 10일 초과 여부에 따라 기준 시점 선택
        if group['timestamp'].max() < cutoff:
            # 아직 10일이 지나지 않은 영상: 최신
            end_snap = group.sort_values('timestamp').iloc[-1]
        else:
            # 10일 지난 영상: 10일 시점 직후 첫 스냅샷
            end_snap = group[group['timestamp'] >= cutoff].sort_values('timestamp').iloc[0]
        return end_snap

    end_snaps = df.groupby('video_id').apply(pick_end_snap)

    # 3) view 변화량 계산
    view0 = first_snaps['view_count']
    view_end = end_snaps['view_count']
    delta_views = view_end - view0

    return delta_views.rename("delta_views")


def compute_video_gain_scores( # 채널의 gain index를 
    channel_df: pd.DataFrame,
    end_subs = int,
    total_views = int,
    c: float = 100.0,
    days: int = 10
) -> pd.DataFrame:
    """
    1) 채널 GainIndex 계산
    2) aggregate_views_within_days로 영상별 조회수 변화량 집계
    3) 조회수 비중대로 채널 지표 분배 → 영상별 Gain Score 산출
    """

    r0 = end_subs / total_views 
    # 1) 채널 지표
    gain_chan = compute_channel_gain_index(channel_df, r0=r0, c=c, days=days)

    # 2) 영상별 delta_views
    views_series = aggregate_views_within_days(channel_df, days=days)

    # 3) 가중치(조회수 비중) 계산
    weights = views_series / total_views

    # 4) 영상별 Gain Score
    scores = gain_chan * weights

    return scores.rename("gain_score").reset_index()  # columns: ['video_id','gain_score']