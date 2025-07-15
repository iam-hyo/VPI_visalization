import pandas as pd
import numpy as np

def compute_gain_score(ch_df: pd.DataFrame, days: int = 14) -> pd.DataFrame:
    # ---------- 날짜 정리 ----------
    ch_df['timestamp'] = pd.to_datetime(
        ch_df['timestamp'], utc=True, errors='coerce'
    ).dt.normalize()
    ch_df['published_at'] = pd.to_datetime(
        ch_df['published_at'], utc=True, errors='coerce'
    ).dt.normalize()

    # ---------- 롱폼 영상 필터링 ----------
    video_df = ch_df[ch_df['is_short'] == False].copy()
    if video_df.empty:
        raise ValueError("❌ 분석 가능한 롱폼 영상 데이터가 없습니다.")

    # ---------- 일별 조회수 피벗 ----------
    video_daily = (
        video_df
        .sort_values('timestamp')
        .groupby(['video_id', 'timestamp'])
        .tail(1)
    )
    pivot_views = (
        video_daily
        .pivot_table(
            index='video_id',
            columns='timestamp',
            values='view_count',
            aggfunc='first'
        )
        .sort_index(axis=1)
    )

    # ---------- 분석 기간 제한 & 일별 증가량 계산 ----------
    if pivot_views.shape[1] > days:
        pivot_views = pivot_views.iloc[:, :days]
    views_diff = pivot_views.diff(axis=1).fillna(0).clip(lower=0)

    # ---------- mean_view_ratio 계산 ----------
    views_long = (
        pivot_views
        .reset_index()
        .melt(id_vars='video_id', var_name='date', value_name='views')
        .dropna(subset=['views'])
    )
    pub = video_df[['video_id', 'published_at']].drop_duplicates()
    views_long = views_long.merge(pub, on='video_id')
    views_long['date'] = pd.to_datetime(views_long['date'], utc=True)
    views_long['published_at'] = pd.to_datetime(views_long['published_at'], utc=True)
    views_long['day_offset'] = (
        views_long['date'] - views_long['published_at']
    ).dt.days
    views_long = views_long[views_long['day_offset'].between(0, days-1)]

    views_by_offset = views_long.pivot_table(
        index='video_id',
        columns='day_offset',
        values='views',
        aggfunc='first'
    )
    avg_views_per_offset = views_by_offset.mean(axis=0)
    ratio_matrix = views_by_offset.div(avg_views_per_offset, axis=1)
    mean_view_ratio = (
        ratio_matrix.mean(axis=1)
        .reindex(pivot_views.index)
        .fillna(0)
    )

    # ---------- 구독자 테이블 구성 ----------
    subs_df = (
        video_df
        .sort_values('timestamp')
        .drop_duplicates('timestamp')[['timestamp', 'subscriber_count']]
        .dropna()
        .sort_values('timestamp')
    )

    # ---------- subs_per_view 계산 ----------
    subs_per_view_list = []
    for i in range(1, len(subs_df)):
        st0 = subs_df.iloc[i-1]['timestamp']
        st1 = subs_df.iloc[i]['timestamp']
        gain = (
            subs_df.iloc[i]['subscriber_count'] -
            subs_df.iloc[i-1]['subscriber_count']
        )
        period_views = views_diff.loc[
            :, (views_diff.columns > st0) & (views_diff.columns <= st1)
        ].sum().sum()
        if gain > 0 and period_views > 0:
            subs_per_view_list.append(gain / period_views)
    if subs_per_view_list:
        subs_per_view = np.mean(subs_per_view_list)
    else:
        subs_diff = (
            subs_df['subscriber_count'].iloc[-1] -
            subs_df['subscriber_count'].iloc[0]
        ) if not subs_df.empty else 0
        total_views_all = views_diff.sum().sum()
        subs_per_view = (
            subs_diff / total_views_all
            if total_views_all > 0 else 0
        )

    # ---------- 일별 추정 구독자 증가량 ----------
    daily_estimated_subs = views_diff.sum(axis=0) * subs_per_view

    # ---------- 영상별 구독자 분배 ----------
    est_subs_by_video = views_diff.copy()
    for day in est_subs_by_video.columns:
        tv = views_diff[day].sum()
        if tv > 0:
            est_subs_by_video[day] = (
                views_diff[day] / tv * daily_estimated_subs[day]
            )
        else:
            est_subs_by_video[day] = 0
    est_subs_by_video_total = est_subs_by_video.sum(axis=1)

    # ---------- 전체 구독자 증가량 스케일링 ----------
    subs_diff = (
        subs_df['subscriber_count'].iloc[-1] -
        subs_df['subscriber_count'].iloc[0]
    ) if not subs_df.empty else 0
    total_est = est_subs_by_video_total.sum()
    if total_est > 0:
        est_subs_by_video_total *= subs_diff / total_est

    # ---------- Gain Index: estimated_subs Min-Max 정규화 ----------
    es = est_subs_by_video_total
    if es.max() > es.min():
        gain_score1 = (es - es.min()) / (es.max() - es.min())*2
    else:
        gain_score1 = pd.Series(2.0, index=es.index)

    # ---------- 결과 반환 ----------
    result_df = pd.DataFrame({
        'video_id': pivot_views.index,
        'retention_score': mean_view_ratio,
        'estimated_subs': est_subs_by_video_total,
        'gain_score2': gain_score1
    }).reset_index(drop=True)
    result_df = result_df.replace(0, np.nan)
    result_df = result_df.fillna("N/A")

    return result_df
