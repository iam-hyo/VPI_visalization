import pandas as pd  # 데이터프레임 처리
from utils.conversion_Index.apply_hyojun_index import aggregate_views_within_days
from utils.metrics import parse_published_at

def compute_video_subscriber_contributions(
    ch_df: pd.DataFrame,
    result_L: pd.DataFrame,
    daily_avg: float,
    correction: float = 0.8,
    max_days: int = 14
) -> pd.DataFrame:
    """
    1) max_days 이내에 업로드된 영상 중 long-form(Shorts 제외)만 필터링
    2) 영상별 view_delta 계산 → diff 보정
    3) daily_avg 분배
    4) 분배 합(total_contrib) == daily_avg 인지 디버깅 출력
    5) ['video_id','subs_contrib'] 반환
    """
    # 1) 최근 max_days 일 내 영상만
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=max_days)
    recent = ch_df[parse_published_at(ch_df['published_at']) >= cutoff]

    # 1a) long-form만 골라내기 (예: is_short 컬럼이 False인 경우)
    #     만약 다른 기준(column)이면 그걸로 교체하세요.
    long_form = recent[recent['is_short'] == False]
    print(f"[DEBUG] {len(long_form)} long-form videos in last {max_days} days")

    # 2) 영상별 view_delta 계산 (Series: index=video_id)
    view_delta = aggregate_views_within_days(long_form, days=1)

    # 3) diff DataFrame 생성 & 보정
    diff_df = view_delta.rename('diff').reset_index()   # columns=['video_id','diff']
    diff_df['diff'] *= correction                       # 보정 계수 적용

    # 4) daily_avg 분배
    total_diff = diff_df['diff'].sum()
    if total_diff > 0:
        diff_df['subs_contrib'] = diff_df['diff'] / total_diff * daily_avg
    else:
        diff_df['subs_contrib'] = 0

    # 4a) 디버깅: 분배된 구독자 기여도 총합이 daily_avg와 같은지 확인
    total_contrib = diff_df['subs_contrib'].sum()
    print(f"[DEBUG] sum(subs_contrib)={total_contrib:.2f}, expected daily_avg={daily_avg:.2f}")

    # 5) 최종 반환
    return diff_df[['video_id', 'subs_contrib']]
