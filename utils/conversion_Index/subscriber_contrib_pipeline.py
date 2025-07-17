import pandas as pd
from datetime import date, timedelta, datetime
from utils.conversion_Index.subscriber_contrib_func import (
    ensure_daily_views,
    compute_view_increments,
    allocate_subs_contrib
)
from utils.supabase.fetch_vid_metrics import (
    get_last_calculated_at,
    upsert_subs_contrib
)

def run_pipeline(
    ch_df: pd.DataFrame,
    daily_cumulative_view_count_df_long: pd.DataFrame,
    channel_id: str,
    estimated_daily_subscribers: pd.DataFrame,
    days: int
):
    """
    마지막 계산일 이후부터 오늘까지 구독자 기여도를 계산 후 DB에 업로드합니다.

    Parameters:
    - ch_df: ['video_id','timestamp','view_count','subscriber_count']
    - daily_cumulative_view_count_df_long: ['day','Estimated Subscribers']
    - channel_id: 채널 ID
    - days: 분석 기간 (일)
    """
    last = get_last_calculated_at(channel_id)
    # last = None
    today = date.today().isoformat()
    end_dt = ch_df['timestamp'].max().date()
    # import streamlit as st
    # st.write(f"Last calculated at: {last}") 
    # st.write(f"End date: {today}")
    if last == today:
        return

    # 1) 일별 구독자 증분 계산
    subs_df = daily_cumulative_view_count_df_long.copy()
    subs_df['day'] = pd.to_datetime(subs_df['day']).dt.date
    subs = estimated_daily_subscribers.set_index('Date')['Estimated Subscribers']
    subs_delta = subs.diff().fillna(0)

    # 2) 기간 내 일별 view_count 보간 및 증가량 계산
    daily_views = ensure_daily_views(ch_df, days)
    view_deltas = compute_view_increments(daily_views)
    # st.header("Debug: view_deltas 👏👏👏👏")
    # st.dataframe(view_deltas, use_container_width=True)

    # 3) 처리 대상 기간 필터 및 디버깅
    start_date = last + timedelta(days=1) if last else end_dt - timedelta(days=days - 1)

    #디버깅 출력
    # st.subheader("✅ 날짜 타입 점검 및 subs_delta 인덱스 확인")
    # st.write(f"start_date: {start_date} ({type(start_date)})")
    # st.write(f"end_dt: {end_dt} ({type(end_dt)})")
    # st.write(f"subs_delta index dtype: {subs_delta.index.dtype}")
    # st.write(f"subs_delta index preview: {subs_delta.index[:5]}")

    # (1) 날짜 역순 방지
    if start_date > end_dt:
        # st.warning("🚫 날짜 범위가 잘못되었습니다: start_date > end_dt. 계산을 생략합니다.")
        # st.write(f"💡 DB 최신 계산일 (last): {last}")
        # st.write(f"💡 수집된 데이터 최신일 (end_dt): {end_dt}")
        # st.write(f"➡️ 계산 대상 범위: {start_date} ~ {end_dt}")
        return

    # (2) subs_delta index 타입 보정 (object 또는 timestamp → date)
    if not isinstance(subs_delta.index[0], (pd.Timestamp, date)):
        subs_delta.index = pd.to_datetime(subs_delta.index, errors='coerce')
    # subs_delta.index = subs_delta.index.map(lambda x: x.date()) # 확실하게 date로 변환

    # (4) 슬라이싱
    mask = (view_deltas['day'] >= start_date) & (view_deltas['day'] <= end_dt)
    view_deltas = view_deltas.loc[mask]

    subs_delta = subs_delta.loc[start_date:end_dt]

    # 최종 결과 확인
    # st.subheader("🎯 Debug: subs_delta 👏👏👏👏")
    # st.dataframe(subs_delta, use_container_width=True)

    # 4) 구독자 기여도 분배 및 합산
    alloc = allocate_subs_contrib(view_deltas, subs_delta)
    # st.header("Debug: alloc")
    # st.dataframe(alloc, use_container_width=True )
    result = alloc.groupby('video_id')['subs_contrib'].sum().reset_index()

    # 5) DB 업로드
    result['channel_id'] = channel_id
    result['calculated_at'] = today
    upsert_subs_contrib(result)