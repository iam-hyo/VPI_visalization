# pages/2_ChannelDetail.py
import streamlit as st
from utils.data_loader import load_processed_data, load_channel_meta
from utils.metrics import (
    get_subscriber_metrics, avg_views, moving_average_views,
    calculate_contribution, video_contribution_by_type, get_recent_videos
)
from components.sidebar import render_sidebar
from components.charts import draw_line_chart, draw_pie_chart
from components.expander import render_video_expander

def main():
    df = load_processed_data("data/processed_data_v2.csv")
    channel_meta = load_channel_meta("data/channel_meta.json")

    channel_id, growth, daily_avg = render_sidebar(df, channel_meta)
    ch_df = df[df["channel_id"] == channel_id]

    st.header(channel_meta[channel_id]["channel_title"])
    st.metric("10일 구독자 증가율", f"{growth:.1%}")
    st.metric("10일 일평균 증가량", f"{daily_avg:,}명")

    # Shorts vs Long-form 평균 조회수
    col1, col2 = st.columns(2)
    with col1:
        st.write("Shorts 평균 조회수", int(avg_views(ch_df, 10, True)))
    with col2:
        st.write("Long-form 평균 조회수", int(avg_views(ch_df, 10, False)))

    # 이동평균 차트
    ma_df = moving_average_views(ch_df, window=5)
    draw_line_chart(ma_df["published_at"], ma_df["ma_view_count"], "조회수 이동평균")

    # 기여도 파이차트
    contrib_df = calculate_contribution(ch_df)
    draw_pie_chart(contrib_df["video_id"], contrib_df["contribution"], "영상별 기여도")
    type_df = video_contribution_by_type(ch_df)
    draw_pie_chart(type_df["type"], type_df["contribution"], "Shorts vs Long")

    # 최근 영상 Expander
    st.subheader("최근 10일 영상 상세")
    recent = get_recent_videos(ch_df, 10)
    for row in recent.itertuples():
        render_video_expander(row, ch_df)

if __name__ == "__main__":
    main()
