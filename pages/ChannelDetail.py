# pages/2_ChannelDetail.py
import streamlit as st
import pandas as np
import streamlit.components.v1 as components
from streamlit.components.v1 import html
from utils.data_loader import load_processed_data, load_channel_meta
from utils.metrics import (
    get_subscriber_metrics, avg_views, 
    avg_view_by_days_since_published, format_korean_count, parse_published_at
)
from utils.apply_hyojun_index import compute_video_gain_scores, aggregate_views_within_days
from components.charts import render_avg_views_table, render_avg_views_line_chart
from components.video_card_st import render_video_card
from components.channel_nameCard import render_name_card
import base64
import requests

def img_url_to_base64(url):
    response = requests.get(url)
    return base64.b64encode(response.content).decode()

st.set_page_config(
    page_icon="📺",
    layout="wide",                    # 필요에 따라 'centered'로 바꿔도 됩니다
    initial_sidebar_state="collapsed" # 'collapsed', 'expanded', 또는 'auto'
)

def main():
    df = load_processed_data("data/processed_data_v2.csv")
    channel_meta = load_channel_meta("data/channel_meta.json")

    channel_id = st.query_params.get("channel_id")
    ch_df = df[df["channel_id"] == channel_id]
    growth, daily_avg, end, start = get_subscriber_metrics(ch_df, 30)

    ch_df = ch_df.copy()
    ch_df['published_at_dt'] = parse_published_at(ch_df['published_at'])
    ch_df['day_since_pub'] = (ch_df['timestamp'] - ch_df['published_at_dt']).dt.days + 1 #공개 후 경과일 계산 (1일 차부터)

    #==========================UI랜더링=========================
    render_name_card(channel_meta, channel_id, ch_df)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("구독자 수", f"{end:,}명") 
    with col2:
        st.metric("총 영상 수", f"{channel_meta[channel_id]['video_count']:,}개")
    total_view = channel_meta[channel_id]['total_view_count']
    formated_total_view = format_korean_count(total_view)
    with col3:
        st.metric("총 조회수", f"{formated_total_view}회")
    with col4:
        st.metric("구독자 증가수", f"{growth:,}명")
    with col5:
        st.metric("30일 일평균 구독자 증가량", f"{daily_avg:,.1f}명")
    st.write("---")
   
    # Shorts vs Long-form 평균 조회수
    st.header("영상 통계량👑")
    st.write(ch_df)
    col1, col2 = st.columns(2)
    with col1: # 롱폼
        long_metrics, result_L = avg_view_by_days_since_published(
            ch_df,
            max_days=30,
            is_short=False
        )
        
        st.markdown("#### :green-badge[Long Form] 공개 이후 평균 조회수")
        st.metric(label="Long-form 평균 조회수", value=f"{int(avg_views(ch_df, 10, False)):,}")
        render_avg_views_table(long_metrics)
        render_avg_views_line_chart(result_L, "")
        
    with col2:
        # 숏폼
        short_metrics, result_S = avg_view_by_days_since_published(
            ch_df,
            max_days=30,
            is_short=True
        )
        st.markdown("#### :blue-badge[Short Form] 공개 이후 평균 조회수")
        st.metric(label="Shorts 평균 조회수", value=f"{int(avg_views(ch_df, 10, True)):,}")
        render_avg_views_table(short_metrics)
        render_avg_views_line_chart(result_S, "")
    
    #─────────────────────────────────────────────────────────── gainscore 계산 시작
    # 1) per-video Gain Score 계산
    #    반환값: DataFrame with columns ['video_id','gain_score']
    video_gain_df = compute_video_gain_scores(
        channel_df   = ch_df,
        end_subs     = end,
        total_views  = total_view,
        c            = 100.0,
        days         = 10
    )
    # ──────────────────────────────────────────────────────────
    # 최근 영상 Expander
    st.subheader("최근 영상 상세")
    
    # 1) 롱폼/숏폼 필터링 탭
    tab_all, tab_longs, tab_shorts = st.tabs(["전체영상", "롱폼", "쇼츠"])
    
    # 2) 탭별 데이터 필터링 함수
    def filter_by_tab(df, tab_name):
        if tab_name == "쇼츠":
            return df[df['is_short'] == True]
        elif tab_name == "롱폼":
            return df[df['is_short'] == False]
        return df

    for tab_name, tab in zip(["전체영상", "쇼츠", "롱폼"], [tab_all, tab_shorts, tab_longs]):
        with tab:
            # 3) 탭별 필터링
            sub = filter_by_tab(ch_df, tab_name)

            # 4) 최신 스냅샷 기준으로 video_id별 최신 row만
            update_video = (
                sub.sort_values('timestamp', ascending=False)
                   .drop_duplicates(subset='video_id', keep='first')
            )

            # 5) Gain Score 머지
            update_video = (
                update_video
                .merge(video_gain_df, on='video_id', how='left')
                .fillna({'gain_score': 0})     # 계산 누락된 경우 0으로
            )

            # 6) 정렬 기준 선택
            col1, col2 = st.columns([3,1])
            col1.markdown(f"**총 영상개수: {len(update_video):,}개**")
            sort_option = col2.selectbox(
                "정렬 순서",
                ["최신순", "조회수순", "기여도순"],
                index=0,
                key=f"sort-{tab_name}"
            )

            if sort_option == "최신순":
                update_video = update_video.sort_values('published_at', ascending=False)
            elif sort_option == "조회수순":
                update_video = update_video.sort_values('view_count', ascending=False)
            else:  # 기여도순
                update_video = update_video.sort_values('gain_score', ascending=False)
            
            #여기에 칼럼 업데이트-------------------------------------------------------
            map_L = result_L.set_index('day')['avg_view_count'].to_dict()
            map_S = result_S.set_index('day')['avg_view_count'].to_dict()
            # 2) update_video DataFrame 준비

            # 3) 기본은 Long-form 맵으로 채우고
            update_video['expected_views'] = update_video['day_since_pub'].map(map_L)

            # 4) Shorts인 행만 Shorts 맵으로 덮어쓰기
            mask_shorts = update_video['is_short']
            update_video.loc[mask_shorts, 'expected_views'] = (
                update_video.loc[mask_shorts, 'day_since_pub']
                            .map(map_S)
            )

            # 5) NaN은 0으로, 정수형으로 변환
            update_video['expected_views'] = (
                update_video['expected_views']
                .fillna(0)
                .astype(int)
            )

            #----------------------------------------------------
            # 7) 각 영상 렌더링
            for _, row in update_video.iterrows():
                vid = row["video_id"]
                # 해당 영상 전체 스냅샷
                snapshot_df = ch_df[ch_df["video_id"] == vid].copy()
                # 올바른 metrics_df 선택
                metrics_df  = result_S if row["is_short"] else result_L

                render_video_card(
                    row=           row,
                    snapshot_df=   snapshot_df,
                    metrics_df=    metrics_df,
                    tab_name = tab_name
    )

if __name__ == "__main__":
    main()