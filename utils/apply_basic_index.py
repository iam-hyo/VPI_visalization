import pandas as pd
import numpy as np

def compute_gain_score(ch_df: pd.DataFrame, ch_snap: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    # ---------- 날짜 정리 ----------
    ch_df['timestamp'] = pd.to_datetime(
        ch_df['timestamp'], utc=True, errors='coerce'
    ).dt.date
    ch_df['published_at'] = pd.to_datetime(
        ch_df['published_at'], utc=True, errors='coerce'
    ).dt.date

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

    # ---------- subs_diff만 ch_snap에서 불러옴 ----------
    ch_snap = ch_snap.sort_values('collected_at')
    if not ch_snap.empty:
        subs_diff = ch_snap['subscriber_count'].iloc[-1] - ch_snap['subscriber_count'].iloc[0]
    else:
        subs_diff = 0

    # ---------- 조회수 변화량 합계로 날짜별 구독자 분배 ----------
    date_totals = views_diff.sum(axis=0)
    sum_views = date_totals.sum()
    if sum_views > 0:
        daily_estimated_subs = date_totals / sum_views * subs_diff
    else:
        daily_estimated_subs = date_totals * 0

    #daily_estimated_subs.to_frame("daily_estimated_subs").to_csv("data/daily_estimated_subs.csv")

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
    #est_subs_by_video.to_csv("data/est_subs_by_video.csv")
    #est_subs_by_video_total.to_frame("est_subs_by_video_total").to_csv("data/est_subs_by_video_total.csv")

    # ---------- Gain Index: estimated_subs Min-Max 정규화 ----------
    es = est_subs_by_video_total
    if es.max() > es.min():
        gain_score1 = (es - es.min()) / (es.max() - es.min()) * 1.8 + 0.2
    else:
        gain_score1 = pd.Series(2.0, index=es.index)

    # ---------- 결과 반환 ----------
    result_df = pd.DataFrame({
        'video_id': pivot_views.index,
        'retention_score': mean_view_ratio,
        'estimated_subs': est_subs_by_video_total,
        'gain_score2': gain_score1
    }).reset_index(drop=True)
    result_df['estimated_subs'] = result_df['estimated_subs'].replace(0, np.nan)
    result_df['gain_score2'] = result_df['gain_score2'].replace(0, np.nan)

    # NaN을 'N/A' 문자열로 변환
    result_df = result_df.astype(object).where(result_df.notnull(), 'N/A')
    return result_df
