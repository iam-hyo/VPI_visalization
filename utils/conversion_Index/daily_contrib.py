import pandas as pd

def compute_daily_video_subscriber_contributions_for_day(
    ch_df: pd.DataFrame,
    result_L: pd.DataFrame,
    date: pd.Timestamp,
    daily_delta: float,
    correction: float = 0.8,
    max_days: int = 14
) -> pd.DataFrame:
    """
    특정 날짜(date)에 대한 영상별 구독자 기여량을 계산합니다.

    - 해당 날짜 스냅샷에서 각 영상의 조회수 증분(actual_delta)
    - 기대 조회수 증분(expected_delta) 대비 보정 후(diff)
    - 일일 구독자 증가량(daily_delta)을 diff 비중으로 분배

    Parameters:
    - ch_df: 전체 채널 스냅샷 DataFrame (timestamp, video_id, view_count, day_since_pub, is_short)
    - result_L: DataFrame ['day','avg_view_count']
    - date: 계산할 날짜 (pd.Timestamp.date)
    - daily_delta: 그날 채널 구독자 증가량
    - correction: 보정 계수
    - max_days: 영향 기간 최대일

    Returns:
    - DataFrame ['video_id','subs_contrib']
    """
    # 1) 그날 롱폼 영상 스냅샷 필터
    df_day = ch_df[
        (ch_df['timestamp'].dt.date == date) &
        (ch_df['is_short']==False) &
        (ch_df['day_since_pub']<max_days)
    ].copy()

    if df_day.empty:
        return pd.DataFrame(columns=['video_id','subs_contrib'])

    # 2) 각 영상의 그날 마지막 스냅샷
    last_snap = (
        df_day.sort_values('timestamp')
              .groupby('video_id').last()
              .reset_index()
    )

    # 3) 그날 이전 스냅샷(하루 전) 가져오기
    df_prev = ch_df[
        (ch_df['timestamp'].dt.date < date) &
        (ch_df['is_short']==False) &
        (ch_df['day_since_pub']<max_days)
    ].copy()
    prev_snap = (
        df_prev.sort_values('timestamp')
               .groupby('video_id').last()
               .reset_index()[['video_id','view_count']]
    )

    # 4) actual_delta 계산
    merged = last_snap.merge(
        prev_snap, on='video_id', how='left', suffixes=('','_prev')
    )
    merged['view_count_prev'] = merged['view_count_prev'].fillna(0)
    merged['actual_delta'] = merged['view_count'] - merged['view_count_prev']

    # 5) expected_delta 계산
    exp_map = result_L.set_index('day')['avg_view_count'].to_dict()
    merged['expected'] = merged['day_since_pub'].map(exp_map).fillna(0)
    merged['prev_expected'] = merged['day_since_pub'].sub(1).map(exp_map).fillna(0)
    merged['expected_delta'] = merged['expected'] - merged['prev_expected']

    # 6) diff = actual_delta - correction * expected_delta (clip>=0)
    merged['diff'] = (
        merged['actual_delta'] - correction * merged['expected_delta']
    ).clip(lower=0)

    # 7) 전체 diff 합
    total_diff = merged['diff'].sum()

    # 8) subs_contrib 계산
    if total_diff > 0:
        merged['subs_contrib'] = merged['diff'] / total_diff * daily_delta
    else:
        merged['subs_contrib'] = 0.0

    # 9) 반환: video_id, subs_contrib
    return merged[['video_id','subs_contrib']]
