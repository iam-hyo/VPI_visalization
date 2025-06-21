import streamlit as st


def render_channel_card(channel_id: str, meta: dict, stats: dict):
    """
    채널 카드 UI 컴포넌트

    Parameters
    ----------
    channel_id : str
        채널 ID
    meta : dict
        채널 이름, 썸네일 URL, 카테고리 등
    stats : dict
        subs_diff: 구독자 증가량
        avg_views: 평균 조회수
        short_ratio: Shorts 비율 (0~1)
    """

    col1, col2 = st.columns([1, 4])
    with col1:
        profile_url = meta.get("profile_image", "")
        if profile_url:
            st.image(profile_url, width=80)
        else:
            print("이미지가 없습니다.")
            st.image("https://via.placeholder.com/80x80?text=No+Image", width=80)

    with col2:
        channel_name = meta.get("channel_title", "Unknown Channel")
        channel_url = f"/ChannelDetail?channel_id={channel_id}"
        category = meta.get("category", "N/A")

        st.markdown(f"### [{channel_name}]({channel_url})")
        st.markdown(f"- 🧾 카테고리: `{category}`")
        st.markdown(f"- 📈 구독자 증가량: `{stats.get('subs_diff', 0):+,}`명")
        st.markdown(f"- 🎞 Shorts 비율: `{stats.get('short_ratio', 0.0):.0%}`")
        st.markdown(f"- 📊 평균 조회수: `{stats.get('avg_views', 0):,}`회")

    st.markdown("---")
