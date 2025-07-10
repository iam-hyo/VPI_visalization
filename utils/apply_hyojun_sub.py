import os                                      # 파일 존재 여부 확인
import pandas as pd                            # CSV 입출력
from utils.subscriber_contrib import compute_video_subscriber_contributions
from utils.daily_contrib import compute_daily_video_subscriber_contributions_for_day
from utils.metrics import get_subscriber_metrics

# CSV 파일 경로 (전체 채널+영상 데이터)
SUBS_FILE = 'data/subs_contrib.csv'


def load_subs(channel_id: str) -> dict:
    """
    CSV에서 해당 채널의 subs_contrib 매핑 읽어 반환
    :param channel_id: 채널 고유 ID
    :return: {video_id: subs_contrib}
    """
    # Debug
    print(f"[DEBUG] load_subs() for channel {channel_id}")
    if os.path.exists(SUBS_FILE):
        df = pd.read_csv(SUBS_FILE)
        df_ch = df[df['channel_id'] == channel_id]     # 채널 필터
        mapping = dict(zip(df_ch['video_id'], df_ch['subs_contrib']))
        print(f"[DEBUG] Found {len(mapping)} subs entries")
        return mapping
    print(f"[DEBUG] No SUBS_FILE found, returning empty dict")
    return {}


def save_subs(subs_dict: dict, channel_id: str):
    """
    subs_dict를 CSV에 병합/덮어쓰기
    :param subs_dict: {video_id: subs_contrib}
    :param channel_id: 채널 고유 ID
    """
    # Debug
    print(f"[DEBUG] save_subs() for channel {channel_id}, entries={len(subs_dict)}")
    # 새로운 DataFrame 생성
    new_df = pd.DataFrame([
        {'channel_id': channel_id, 'video_id': vid, 'subs_contrib': cnt}
        for vid, cnt in subs_dict.items()
    ])
    if os.path.exists(SUBS_FILE):
        old_df = pd.read_csv(SUBS_FILE)
        # 병합 후 마지막 값을 우선
        df = pd.concat([old_df, new_df], ignore_index=True)
        df = df.drop_duplicates(subset=['channel_id', 'video_id'], keep='last')
    else:
        df = new_df
    df.to_csv(SUBS_FILE, index=False)
    print(f"[DEBUG] SUBS_FILE saved with {len(df)} total rows")


def initial_batch(ch_df: pd.DataFrame, result_L: pd.DataFrame, daily_avg: float):
    """
    최초 배치: 상수 daily_avg로 영상별 누적 subs_contrib 계산 후 저장
    """
    channel_id = ch_df['channel_id'].iloc[0]
    # subs_contrib 계산
    subs_df = compute_video_subscriber_contributions(
        ch_df,
        result_L,
        daily_avg=daily_avg,
        correction=0.8,
        max_days=14
    )
    subs_dict = dict(zip(subs_df['video_id'], subs_df['subs_contrib']))
    save_subs(subs_dict, channel_id)
    print(f"[DEBUG] initial_batch() done for {channel_id}")


def incremental_update(
    ch_df: pd.DataFrame,
    result_L: pd.DataFrame
):
    """
    일일 업데이트: 오늘치 구독자 기여도 계산 후 누적 저장

    :param ch_df: 채널 전체 영상 데이터 (timestamp, subscriber_count 등 포함)
    :param result_L: gain score 계산 결과 DataFrame
    """
    # 1) 채널 ID 추출
    channel_id = ch_df['channel_id'].iloc[0]
    print(f"[DEBUG] incremental_update() start for {channel_id}")

    # 2) 오늘 날짜 결정 (최대 timestamp 기준)
    today_date = ch_df['timestamp'].dt.date.max()
    print(f"[DEBUG] today_date = {today_date}")

    # 3) 오늘치 스냅샷만 추출
    day_df = ch_df[ch_df['timestamp'].dt.date == today_date]
    if day_df.empty:
        print(f"[DEBUG] No data for today ({today_date}) – skipping update.")
        return

    # 4) 하루 시작·끝 구독자 수 차이 계산
    s0 = day_df['subscriber_count'].iloc[0]
    s1 = day_df['subscriber_count'].iloc[-1]
    daily_delta = s1 - s0
    print(f"[DEBUG] subscriber delta for {today_date}: {daily_delta}")

    # 5) 오늘치 subs_contrib 계산 (date, daily_delta 필수 인자로 전달)
    daily_dict = compute_daily_video_subscriber_contributions_for_day(
        ch_df=ch_df,
        result_L=result_L,
        date=today_date,
        daily_delta=daily_delta,
        correction=0.8,
        max_days=14
    )
    print(f"[DEBUG] computed today contributions: {daily_dict}")

    # 6) 기존 subs 불러와 누적 합산
    prev = load_subs(channel_id)
    for vid, cnt in daily_dict.items():
        # cnt 가 str 일 수 있으니 float 으로 변환
        try:
            cnt_f = float(cnt)
        except (ValueError, TypeError):
            cnt_f = 0.0
        # prev.get 도 str 일 수 있으니 float 으로 변환
        base = prev.get(vid, 0)
        try:
            base_f = float(base)
        except (ValueError, TypeError):
            base_f = 0.0
        prev[vid] = base_f + cnt_f

    # 7) 갱신된 dict를 CSV에 저장
    save_subs(prev, channel_id)
    print(f"[DEBUG] incremental_update() done for {channel_id}, total entries now={len(prev)}")
