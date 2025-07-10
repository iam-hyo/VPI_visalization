# pages/2_ChannelDetail.py
import streamlit as st
import pandas as pd
import json, datetime, requests, base64

from utils.apply_basic_index import compute_gain_score
from utils.apply_hyojun_index import compute_video_gain_scores
from utils.apply_hyojun_sub import (
    initial_batch,
    incremental_update,
    SUBS_FILE
)
from utils.apply_regression_index import regression_score
from utils.data_loader import load_processed_data, load_channel_meta
from utils.metrics import (
    get_subscriber_metrics, avg_views, 
    avg_view_by_days_since_published, format_korean_count, parse_published_at
)
from components.channel_nameCard import render_name_card
from components.charts import render_avg_views_table, render_avg_views_line_chart
from components.video_card_st import render_video_card

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
    meta_path    = "data/channel_meta.json"
    channel_meta = load_channel_meta(meta_path)
    
    channel_id = st.query_params.get("channel_id")
    channel_name = channel_meta[channel_id]["channel_title"]
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

    col1, col2 = st.columns(2)
    with col1: # 롱폼
        long_metrics, result_L = avg_view_by_days_since_published(
            ch_df,
            max_days    = 30,
            is_short    = False
        )

        st.markdown(f"""
                <span style="
                    background:#5f9aff;
                    color:#fff;
                    padding:2px 6px;
                    border-radius:4px;
                    font-size:0.9em;
                    white-space:nowrap;
                ">Long-form</span> 공개 이후 평균 조회수
                """, unsafe_allow_html=True)
        st.metric(label="Long-form 평균 조회수", value=f"{int(avg_views(ch_df, 10, False)):,}")
        render_avg_views_table(long_metrics)
        render_avg_views_line_chart(result_L, "")
        
    with col2:
        # 숏폼
        short_metrics, result_S = avg_view_by_days_since_published(
            ch_df,
            max_days    = 30,
            is_short    = True
        )
        st.markdown(f"""
        <span style="
            background:#ff5f5f;
            color:#fff;
            padding:2px 6px;
            border-radius:4px;
            font-size:0.9em;
            white-space:nowrap;
        ">Shorts</span> 공개 이후 평균 조회수
        """, unsafe_allow_html=True)
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
        days         = 14
    )

    # 1.5) subscriber_contrib 계산 (채널별 last_run_date 로 관리)
    today_date = datetime.date.today()
    today_str = today_date.isoformat()
    last_run = channel_meta[channel_id].get("last_run_date")
    st.caption(f"[DEBUG] {channel_name} last_run: {last_run}, today: {today_str}")

    if last_run != today_str:
        if last_run is None:
            st.write(f"[DEBUG] initial_batch() start for {channel_id} with daily_avg={daily_avg}")
            initial_batch(ch_df, result_L, daily_avg)      # 초기 계산 with external daily_avg
        else:
            st.write(f"[DEBUG] Performing incremental_update for {channel_id}")
            incremental_update(ch_df, result_L)          # 일일 업데이트
        # 메타 갱신
        channel_meta[channel_id]["last_run_date"] = today_str
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(channel_meta, f, ensure_ascii=False, indent=2)
        st.write(f"[DEBUG] Saved last_run_date={today_str} for {channel_id}")
    else:
        st.write(f":white_check_mark: Channel {channel_id} subs_contrib already updated today.")

    # CSV에서 갱신된 subs_contrib 불러오기
    subs_df = pd.read_csv(SUBS_FILE)                          # 전체 채널 subs
    subs_df_ch = subs_df[subs_df["channel_id"] == channel_id]

    # 1.5) 갱신된 subs_contrib.csv 불러오기
    subs_df = pd.read_csv(SUBS_FILE)  # columns: video_id, subs_contrib

    # 2) 다중이 계산
    # 반환값: DataFrame with columns ['video_id','βᵢ / β_total', 'regression_subs_contrib']
    # 반환값2: DataFrame with columns ['Date','Spread Change']
    coefficient_df, spread_change_df = regression_score(
        ch_df       = ch_df,
        days        = 30,
        channel_id  = channel_id
    )

    # 3) 기본이 계산
    final_score_df = compute_gain_score(
        ch_df1=ch_df,
        days=14
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

            #5.5) sub_Contrib merge
            update_video = update_video.merge(
                subs_df_ch[['video_id', 'subs_contrib']],
                on='video_id', how='left'
            ).fillna({'subs_contrib': 0}) 

            # 6) Standardized Coefficient (βᵢ) 머지
            update_video = (
                update_video
                .merge(coefficient_df, on='video_id', how='left')
                .fillna({'βᵢ / β_total': 0})  # 계산 누락된 경우 0으로
                .fillna({'regression_subs_contrib': 0})  # 계산 누락된 경우 0으로
            )

            # 7) final_score 머지
            update_video = update_video.merge(
                final_score_df,
                on='video_id', how='left'
            ).fillna({'final_score': 0})

            # 8) 정렬 기준 선택
            col1, col2 = st.columns([3,1])
            col1.markdown(f"**총 영상개수: {len(update_video):,}개**")
            sort_option = col2.selectbox(
                "정렬 순서",
                ["최신순", "조회수순", "기여도순"],
                index=0,
                key=f"sort-{tab_name}"
            )

            update_video['published_at_dt'] = pd.to_datetime(update_video['published_at_dt'], errors='coerce')

            if sort_option == "최신순":
                update_video = update_video.sort_values('published_at_dt', ascending=False)
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
    #st.write(coefficient_df)

if __name__ == "__main__":
    main()