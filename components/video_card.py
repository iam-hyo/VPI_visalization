# components/video_card.py
import streamlit as st

def render_video_card(channel_id, meta, stats):
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(meta.get('profile_image'), width=60)
    with col2:
        st.markdown(f"**{meta.get('channel_title')}**")
        st.write(f"- 카테고리: {meta.get('category')}")
        st.write(f"- 구독자 변화: {stats['subs_diff']:,}")
        st.write(f"- 평균 조회수: {stats['avg_views']:,}")
        st.write(f"- Shorts 비율: {stats['short_ratio']:.1%}")
    st.markdown("---")
