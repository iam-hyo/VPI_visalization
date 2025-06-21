# components/expander.py
import streamlit as st
from datetime import datetime
from utils.metrics import calculate_contribution, moving_average_views

def render_video_expander(video_row, all_videos_df):
    video_id = video_row.video_id
    contrib_df = calculate_contribution(all_videos_df)
    contrib = float(contrib_df.set_index("video_id").loc[video_id, "contribution"])
    days_since = (datetime.now() - video_row.published_at).days

    with st.expander(f"{video_row.video_title} ({days_since}일 전)"):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(video_row.thumbnail_url, use_column_width=True)
        with col2:
            st.write(f"조회수: {video_row.view_count:,}")
            st.write(f"기여도: {contrib:.1%}")
            st.write(f"업로드 후 경과일: {days_since}일")

        ma_df = moving_average_views(
            all_videos_df[all_videos_df.video_id == video_id], window=3
        )
        st.line_chart(data=ma_df.set_index("published_at")["ma_view_count"])
