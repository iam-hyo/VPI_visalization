from datetime import timedelta
import numpy as np
import pandas as pd
import streamlit as st
from utils.metrics import parse_published_at

def compute_channel_gain_index(
    channel_df: pd.DataFrame,
    r0: float = 0.01,
    days: int = 10, 
    daily_avg: float = None
) -> float:
    """
    채널 전체의 보정 전환 기여도 (GainIndex_chan) 계산.
    - 기대전환율 r0는 외부에서 주입된 값(예: (end_subs/total_views)/ln(end_subs+c))
    - 실제전환율 r_d는 기간 내 구독자 증가량 ΔS_d / 기간 내 조회수 V_d
    """
    # 1) timestamp 기준 오름차순 보장
    df = channel_df.sort_values('timestamp')

    # 2) 기간 내 조회수 변화량 집계
    views_series = aggregate_views_within_days(df, days=days)
    total_views_in_days = views_series.sum()

    # 3) 기간 시작·끝 구독자 수 (평균 변화량 vs 기간 변화량)
    if daily_avg != None:
        ΔS = daily_avg * days
    else :
        cutoff = df['timestamp'].max() - timedelta(days=days)
        recent = df[df['timestamp'] >= cutoff]
        if len(recent) < 2:
            ΔS = 0
        else:
            start_subs = recent['subscriber_count'].iloc[0]
            end_subs   = recent['subscriber_count'].iloc[-1]
            ΔS = end_subs - start_subs

    # 4) 기대 전환율 (외부 r0 입력값 그대로 사용)
    #    r0 = (end_subs_period/total_views) / ln(end_subs_period + c)
    expected_rate = r0

    # 5) 실제 전환율 r_d = ΔS_d / V_d
    actual_rate = ΔS / total_views_in_days if total_views_in_days > 0 else 0.0
    # st.write(f"ΔS (subs change): {ΔS}, V_d (views): {total_views_in_days}")
    # st.write(f"actual_rate (r_d): {actual_rate:.4f}")

    # 6) 채널 GainIndex = r_d / r0
    GainIndex_chan = actual_rate / expected_rate if expected_rate > 0 else 0.0
    st.write(f"GainIndex_chan (r_d/r0): {GainIndex_chan:.4f}")

    return GainIndex_chan


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
            # 아직 10일이 지나지 않은 영상: 마지막 값
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


def compute_video_gain_scores(
    channel_df: pd.DataFrame,
    end_subs: int,
    total_views: int,
    c: float = 100.0,
    days: int = 10
) -> pd.DataFrame:
    """
    쇼츠 영상을 배제하고 롱폼 영상 기준으로 채널 GainIndex를 계산한 뒤,
    조회수 비중대로 Gain Score를 산출합니다.

    Parameters:
    - channel_df: 전체 시계열 데이터 (timestamp, published_at, view_count,
      subscriber_count, is_short, video_id 포함)
    - end_subs: 기간 종료 시점 누적 구독자 수
    - total_views: 기간 내 전체 조회수 합 (롱폼 기반 계산을 위해 재계산됨)
    - c: 로그 안정화 상수
    - days: 계산 기준 기간 (일)

    Returns:
    DataFrame with columns ['video_id', 'gain_score']
      - gain_score: 롱폼 영상에만 실수 값, 쇼츠는 None
    """
    # 1) 롱폼 영상만 필터링
    long_df = channel_df[channel_df['is_short'] == False].copy()

    # 2) 기준 전환율 r0 설정: (end_subs/total_views) / ln(end_subs + c)
    #    total_views 파라미터는 롱폼 기준으로 재계산하므로 여기서는 end_subs/(sum of all views) 대신 재구성할 수 있음
    #    기본적으로 주어진 total_views로 계산하되, 0 방지 처리
    if total_views > 0:
        r0_baseline = (end_subs / total_views) / np.log(end_subs + c)
    else:
        r0_baseline = 0.0

    # 3) 채널 GainIndex 계산 (롱폼 기준)
    gain_chan = compute_channel_gain_index(
        long_df,
        r0=r0_baseline, 
        days=days
    )

    # 4) 롱폼 영상 조회수 변화량 집계
    views_series = aggregate_views_within_days(long_df, days=days)
    total_views_long = views_series.sum()

    # 5) 롱폼 영상 가중치(조회수 비중)
    if total_views_long > 0:
        weights = views_series / total_views_long
    else:
        weights = views_series * 0.0

    # 6) 영상별 Gain Score 계산 (롱폼)
    gain_scores = gain_chan * weights

    # 7) 전체 영상 리스트와 합치기 (쇼츠는 None)
    unique_videos = channel_df[['video_id', 'is_short']].drop_duplicates(subset='video_id')
    result_df = unique_videos.copy()
    result_df['gain_score'] = result_df['video_id'].map(gain_scores.to_dict())

    # 쇼츠는 '-' 혹은 None으로 처리(여기서는 None)
    result_df.loc[result_df['is_short'], 'gain_score'] = None

    # 8) 반환: ['video_id', 'gain_score'] 형태
    return result_df[['video_id', 'gain_score']]
