import pandas as pd


def ensure_daily_views(ch_df: pd.DataFrame, days: int) -> pd.DataFrame:
    """
    각 video_id별로 지정 기간(days) 내 일별 view_count를 선형 보간하여 반환합니다.

    Parameters:
    - ch_df: DataFrame with columns ['video_id','collected_at','view_count']
    - days: 분석할 일 수

    Returns:
    - daily_views: DataFrame with ['video_id','date','view_count']
    """
    # 기간 설정
    end_date = ch_df['timestamp'].max().date()
    start_date = end_date - pd.Timedelta(days=days-1)
    date_index = pd.date_range(start_date, end_date, freq='D')

    records = []
    for vid, group in ch_df.groupby('video_id'):
        # 인덱스를 날짜로 리샘플링 후 interpolation
        series = (
            group.set_index('timestamp')['view_count']
                 .resample('D')
                 .mean()
                 .reindex(date_index)
                 .interpolate()
        )
        for dt, view in series.items():
            records.append({'video_id': vid, 'day': dt.date(), 'view_count': view})
    return pd.DataFrame(records)


def compute_view_increments(daily_views: pd.DataFrame) -> pd.DataFrame:
    """
    일자별 view_count 증가량(view_delta)을 계산합니다.

    Parameters:
    - daily_views: ['video_id','date','view_count']

    Returns:
    - DataFrame ['video_id','date','view_delta']
    """
    df = daily_views.sort_values(['video_id','day']).copy()
    df['prev_view'] = df.groupby('video_id')['view_count'].shift(1).fillna(0)
    df['view_delta'] = df['view_count'] - df['prev_view']
    return df[['video_id','day','view_delta']]


def allocate_subs_contrib(view_deltas: pd.DataFrame, subs_delta: pd.Series) -> pd.DataFrame:
    """
    조회수 증가 비중에 따라 일별 구독자 증분을 배분합니다.

    Parameters:
    - view_deltas: ['video_id','date','view_delta']
    - subs_delta: pd.Series indexed by date, 값은 해당 날짜 구독자 증분

    Returns:
    - DataFrame ['video_id','day','subs_contrib']
    """
    df = view_deltas.copy()
    df = df[df['view_delta'].notna() & (df['view_delta'] > 0)]  # 1. 안전 필터링: 유효한 값만 남기기
    total = df.groupby('day')['view_delta'].transform('sum')    # 2. 일자별 총합 구하기
    df['subs_contrib'] = df['view_delta'] / total * df['day'].map(subs_delta) # 3. 비율로 구독자 증분 배분
    return df[['video_id','day','subs_contrib']]
