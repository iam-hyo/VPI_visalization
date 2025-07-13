import pandas as pd
import numpy as np

def compute_gain_score(ch_df: pd.DataFrame, days: int = 14) -> pd.DataFrame:
    # channel_id | video_id | title | published_at | is_short | thumbnail_url | timestamp | subscriber_count | day_since_pub | comment_count | like_count | view_count
    # ---------- 날짜 정리 ----------
    ch_df['timestamp'] = pd.to_datetime(ch_df['timestamp'], utc=True, errors='coerce').dt.normalize()
    ch_df['published_at'] = pd.to_datetime(ch_df['published_at'], utc=True, errors='coerce').dt.normalize()

    # ---------- 채널 핸들 추출 및 롱폼 필터링 ----------
    video_df = ch_df[ch_df['is_short'] == False].copy()
    if video_df.empty:
        raise ValueError("❌ 분석 가능한 롱폼 영상 데이터가 없습니다.")

    # ---------- 일별 조회수 피벗 ----------
    video_daily = video_df.sort_values('timestamp').groupby(['video_id', 'timestamp']).tail(1)
    pivot_views = video_daily.pivot_table(index='video_id', columns='timestamp', values='view_count', aggfunc='first')
    pivot_views = pivot_views.sort_index(axis=1)

    # ---------- 분석 기간 제한 ----------
    if pivot_views.shape[1] > days:
        pivot_views = pivot_views.iloc[:, :days]

    views_diff = pivot_views.diff(axis=1).fillna(0).clip(lower=0)

    # ---------- mean_view_ratio 계산 ----------
    avg_first_views_per_day = []
    for i, day in enumerate(pivot_views.columns):
        is_first_day = pivot_views[day].notna() & pivot_views.iloc[:, :i].isna().all(axis=1)
        avg = pivot_views.loc[is_first_day, day].mean()
        avg_first_views_per_day.append(avg)

    mean_view_ratio = []
    for idx, row in pivot_views.iterrows():
        first_day = row.first_valid_index()
        if first_day is not None:
            video_view = row[first_day]
            avg_view = avg_first_views_per_day[list(pivot_views.columns).index(first_day)]
            mean_view_ratio.append(video_view / avg_view if avg_view > 0 else np.nan)
        else:
            mean_view_ratio.append(np.nan)

    # ---------- 구간별 구독자 변화 추정 ----------
    subs_df = (
        video_df.sort_values('timestamp')
        .drop_duplicates('timestamp')[['timestamp', 'subscriber_count']]
        .dropna()
        .sort_values('timestamp')
    )

    sub_changes = []
    for i in range(1, len(subs_df)):
        start_time = subs_df.iloc[i - 1]['timestamp']
        end_time = subs_df.iloc[i]['timestamp']
        start_sub = subs_df.iloc[i - 1]['subscriber_count']
        end_sub = subs_df.iloc[i]['subscriber_count']
        total_gain = end_sub - start_sub

        valid_days = [d for d in pivot_views.columns if start_time <= d <= end_time]
        if not valid_days or total_gain <= 0:
            continue

        sub_views = views_diff[valid_days]
        for day in valid_days:
            total_views = sub_views[day].sum()
            if total_views == 0:
                continue
            day_gain = (sub_views[day] / total_views) * total_gain
            sub_changes.append(day_gain)

    # ---------- 영상별 추정 구독자 증가량 ----------
    if sub_changes:
        est_subs_by_video = pd.concat(sub_changes, axis=1).sum(axis=1)
    else:
        est_subs_by_video = pd.Series(0, index=views_diff.index)

    sub_gain_ratio = est_subs_by_video / est_subs_by_video.sum()

    # ---------- 정규화 및 점수 계산 ----------
    def minmax(x):
        return (x - x.min()) / (x.max() - x.min())

    norm_view_ratio = minmax(pd.Series(mean_view_ratio, index=pivot_views.index)).fillna(0)
    norm_sub_ratio = minmax(sub_gain_ratio).fillna(0)

    raw_score = norm_view_ratio + norm_sub_ratio
    log_scaled_score = np.log1p(raw_score)
    final_score = log_scaled_score / log_scaled_score.sum()

    return pd.DataFrame({
        'video_id': pivot_views.index,
        'final_score': final_score,
        'estimated_subs': est_subs_by_video
    }).reset_index(drop=True)
