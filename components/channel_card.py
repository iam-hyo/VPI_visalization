import streamlit as st
from utils.metrics import format_korean_count

def render_channel_card(channel_id: str, meta: dict, stats: dict):
    """
    채널 카드 UI 컴포넌트

    Parameters
    ----------
    channel_id : str
        채널 ID
    meta : dict
        채널 메타 정보 (이름, 썸네일 URL, 카테고리 등)
    stats : dict
        subscriber_count: 현재 구독자 수 (int)
        subs_diff: 구독자 증가량 (int)
        avg_views: 평균 조회수 (int)
        short_ratio: Shorts 비율 (0~1)
    """
    # 6열 레이아웃: 썸네일, 채널명, 카테고리, 구독자 수, 구독자 증가량, 평균 조회수 & Shorts 비율
    cols = st.columns([2, 4, 2, 2, 2, 3])

    # 1열: 채널 썸네일
    with cols[0]:
        profile_url = meta.get("profile_image", "")
        if profile_url:
            st.image(profile_url, width=80)
        else:
            st.image("https://via.placeholder.com/80x80?text=No+Image", width=80)

    # 2열: 채널명 (링크)
    with cols[1]:
        channel_name = meta.get("channel_title", "Unknown Channel")
        channel_url = f"/ChannelDetail?channel_id={channel_id}"
        st.markdown(f"### [{channel_name}]({channel_url})")

    # 3열: 카테고리 (badge 스타일)
    with cols[2]:
        category = meta.get("category", "N/A")
        st.metric(label="카테고리", value=f"{category}")

    # 4열: 구독자 수
    with cols[3]:
        subscriber_count = stats.get("subscriber_count", 0)
        subscriber_count = format_korean_count(subscriber_count)
        st.metric(label="구독자 수", value=f"{subscriber_count}")

    # 5열: 구독자 증가량
    with cols[4]:
        subs_diff = stats.get("subs_diff", 0)
        st.metric(label="구독자 증가량", value=f"{subs_diff:+,}")

    # 6열: 평균 조회수 (정수) & Shorts 비율 (badge)
    with cols[5]:
        avg_views = stats.get("avg_views", 0)
        short_ratio = stats.get("short_ratio", 0.0)
        video_count = meta.get("video_count", 0)

        st.markdown(f":label: 평균 조회수: `{int(avg_views):,}`회")
        st.markdown(f":label: 쇼츠 비율: `{short_ratio:.0%}`")
        st.markdown(f":label: 총 영상 수: `{video_count:,}`개")

    st.markdown("---")
