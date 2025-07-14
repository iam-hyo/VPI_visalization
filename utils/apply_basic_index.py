import pandas as pd
import numpy as np

def compute_gain_score(ch_df: pd.DataFrame, days: int = 14) -> pd.DataFrame:
    # ---------- 날짜 정리 ----------
    ch_df['timestamp']    = pd.to_datetime(ch_df['timestamp'],    utc=True, errors='coerce').dt.normalize()
    ch_df['published_at'] = pd.to_datetime(ch_df['published_at'], utc=True, errors='coerce').dt.normalize()

    # ---------- 롱폼 영상 필터링 ----------
    video_df = ch_df[ch_df['is_short'] == False].copy()
    if video_df.empty:
        raise ValueError("❌ 분석 가능한 롱폼 영상 데이터가 없습니다.")

    # ---------- 일별 조회수 피벗 ----------
    video_daily = (
        video_df
        .sort_values('timestamp')
        .groupby(['video_id','timestamp'])
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

    # ---------- mean_view_ratio 계산 (업로드 후 경과일 기준) ----------
    views_long = (
        pivot_views
        .reset_index()
        .melt(id_vars='video_id', var_name='date', value_name='views')
        .dropna(subset=['views'])
    )
    pub = video_df[['video_id','published_at']].drop_duplicates()
    views_long = views_long.merge(pub, on='video_id')

    views_long['date']         = pd.to_datetime(views_long['date'],         utc=True)
    views_long['published_at'] = pd.to_datetime(views_long['published_at'], utc=True)
    views_long['day_offset']   = (views_long['date'] - views_long['published_at']).dt.days
    views_long = views_long[views_long['day_offset'].between(0, days-1)]

    views_by_offset = views_long.pivot_table(
        index='video_id',
        columns='day_offset',
        values='views',
        aggfunc='first'
    )
    avg_views_per_offset = views_by_offset.mean(axis=0)
    ratio_matrix = views_by_offset.div(avg_views_per_offset, axis=1)
    mean_view_ratio = ratio_matrix.mean(axis=1).reindex(pivot_views.index).fillna(0)

    # ---------- 구간별 구독자 변화 추정 ----------
    subs_df = (
        video_df.sort_values('timestamp')
                .drop_duplicates('timestamp')[['timestamp','subscriber_count']]
                .dropna()
                .sort_values('timestamp')
    )
    sub_changes = []
    for i in range(1, len(subs_df)):
        start_time = subs_df.iloc[i-1]['timestamp']
        end_time   = subs_df.iloc[i  ]['timestamp']
        gain       = subs_df.iloc[i]['subscriber_count'] - subs_df.iloc[i-1]['subscriber_count']
        valid = [d for d in pivot_views.columns if start_time <= d <= end_time]
        if not valid or gain <= 0:
            continue
        sub_views = views_diff[valid]
        for d in valid:
            tot = sub_views[d].sum()
            if tot <= 0:
                continue
            sub_changes.append((sub_views[d] / tot) * gain)

    if sub_changes:
        est_subs_by_video = pd.concat(sub_changes, axis=1).sum(axis=1)
    else:
        est_subs_by_video = pd.Series(0, index=views_diff.index)

    # ---------- 전체 구독자 증가량과 합 일치시키기 위한 스케일링 ----------
    subs_diff = subs_df['subscriber_count'].iloc[-1] - subs_df['subscriber_count'].iloc[0]
    total_est = est_subs_by_video.sum()
    if total_est > 0:
        scale = subs_diff / total_est
        est_subs_by_video = est_subs_by_video * scale

    sub_gain_ratio = est_subs_by_video / est_subs_by_video.sum()

    # ---------- 정규화 및 최종 스코어 계산 ----------
    def minmax(x): return (x - x.min()) / (x.max() - x.min())

    norm_view_ratio = minmax(mean_view_ratio).fillna(0)
    norm_sub_ratio  = minmax(sub_gain_ratio).fillna(0)
    raw_score       = norm_view_ratio + norm_sub_ratio
    log_scaled      = np.log1p(raw_score)
    final_score     = log_scaled / log_scaled.sum()

    return pd.DataFrame({
        'video_id':       pivot_views.index,
        'final_score':    final_score,
        'estimated_subs': est_subs_by_video
    }).reset_index(drop=True)
