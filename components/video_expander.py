import streamlit as st

def render_video_expander(video_row):
    vid = video_row['video_id']
    title = video_row.get('video_title', '')
    views = video_row.get('view_count', 0)
    is_short = video_row.get('is_short', False)
    thumb_url = video_row.get('thumbnail_url', f"https://img.youtube.com/vi/{vid}/mqdefault.jpg")

    label = f"{'🎞 Shorts' if is_short else '🎬 Long'} | 조회수: {views:,} | 영상 ID: {vid}"

    with st.expander(label):
        if thumb_url :
            st.image(thumb_url, width=320)
        else: 
            st.image("https://img.youtube.com/vi/{vid}/mqdefault.jpg", width=320)
        st.markdown(f"**제목**: {title}")
        st.markdown(f"[YouTube 바로가기](https://www.youtube.com/watch?v={vid})")
