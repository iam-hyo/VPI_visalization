# components/sidebar.py
import streamlit as st
from utils.metrics import get_subscriber_metrics

# channel_id, growth, daily_avg = render_sidebar(df, channel_meta)
def render_sidebar(df, channel_meta):
    st.sidebar.header("채널 선택")
    options = list(channel_meta.keys())
    labels  = {cid: meta.get("channel_title", cid) for cid, meta in channel_meta.items()}

    channel_id = st.sidebar.selectbox(
        "채널",
        options,
        format_func=lambda x: labels[x],
        key="sidebar_channel_select"
    )

    ch_df = df[df['channel_id'] == channel_id]
    growth, daily_avg, end, start = get_subscriber_metrics(ch_df)

    st.sidebar.subheader("10일 구독자 통계")
    st.sidebar.metric("증가율", f"{growth:.1%}")
    st.sidebar.metric("일평균 증가", f"{int(daily_avg):,}명")

    return channel_id, growth, daily_avg, end, start
