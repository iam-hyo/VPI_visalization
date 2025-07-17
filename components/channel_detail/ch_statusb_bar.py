import streamlit as st
from utils.metrics import format_korean_count


def render_status_bar(
    latest_subs: int,
    video_count: int,
    total_view: int,
    initial_date: str,
    subs_diff: int,
    avg_daily_increase: float
) -> None:
    """
    Streamlit UI로 채널 상태 바를 렌더링합니다.

    Args:
        latest_subs: 최신 구독자 수
        video_count: 총 영상 수
        total_view: 총 조회수
        subs_diff: 해당 기간 동안 구독자 증가량
        avg_daily_increase: 일평균 구독자 증가량
    """
    # 5개의 열 생성
    initial_date = initial_date.strftime("%m-%d")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("구독자 수", f"{latest_subs:,}명")

    with col2:
        st.metric("총 영상 수", f"{video_count:,.0f}개")

    # 총 조회수 포맷팅
    formatted_total_view = format_korean_count(total_view)
    with col3:
        st.metric("총 조회수", f"{formatted_total_view}회")

    with col4:
        st.metric(f"{initial_date} 이후 구독자 증가수", f"{subs_diff:,}명")

    with col5:
        st.metric("일평균 구독자 증가량", f"{avg_daily_increase:,.1f}명")

    # 구분선
    st.markdown("---")
