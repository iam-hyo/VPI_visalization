# pages/2_ChannelDetail.py
import streamlit as st
import pandas as pd
import datetime, requests, base64

from utils.apply_basic_index import compute_gain_score
from utils.conversion_Index.apply_hyojun_index import compute_video_gain_scores
from utils.conversion_Index.apply_hyojun_sub import (initial_batch, incremental_update, SUBS_FILE)
from utils.apply_regression_index import regression_score
from utils.metrics import (get_subscriber_metrics, avg_view_by_days_since_published)
from utils.supabase.get_data import fetch_channel, get_channel_video_snapshots, fetch_channel_snapshots
from components.channel_detail.channel_nameCard import render_name_card
from components.channel_detail.charts import render_avg_views_table, render_avg_views_line_chart, render_estimated_subscribers_chart
from components.channel_detail.video_card_st import render_video_card
from components.channel_detail.ch_statusb_bar import render_status_bar

def img_url_to_base64(url):
    response = requests.get(url)
    return base64.b64encode(response.content).decode()

st.set_page_config(
    page_icon="📺",
    layout="wide",                    
    initial_sidebar_state="collapsed" # 'collapsed', 'expanded', 또는 'auto'
)

def main():    
    channel_id = st.query_params.get("channel_id")
    channel_meta = fetch_channel()[channel_id]  #channels 불러오기

    ch_df = get_channel_video_snapshots(channel_id)
    # channel_id | video_id | title | published_at | is_short | thumbnail_url | timestamp | subscriber_count | day_since_pub | comment_count | like_count | view_count
    #ch_df.to_csv("data/ch_df.csv",index=False)
    ch_snap = fetch_channel_snapshots(channel_id).sort_values("collected_at")
    # ch_snap["collected_at"] = pd.to_datetime(ch_snap["collected_at"], utc=True, format='mixed').dt.date
    # ch_snap.to_csv("data/temp.csv", index=False)
    # channel_id | collected_at | subscriber_count | total_view_count | video_count

    video_count = ch_snap.iloc[-1]["video_count"]
    total_view = ch_snap.iloc[-1]["total_view_count"]
    subs_diff, avg_daily_increase, latest_subs = get_subscriber_metrics(ch_snap, 30)

    #==========================UI랜더링=========================
    render_name_card(channel_meta)
    render_status_bar(
        latest_subs=latest_subs,
        video_count=video_count,
        total_view=total_view,
        subs_diff=subs_diff,
        avg_daily_increase=avg_daily_increase,
    )
    #───────────────────────────────────────────────────────────

    # 2) 다중이 계산
    # 반환값: DataFrame with columns ['video_id','βᵢ / β_total', 'regression_subs_contrib', 'retention_index']
    # 반환값2: DataFrame with columns ['Date','Spread Change']
    coefficient_df, spread_change_df = regression_score(
        ch_df       = ch_df,
        ch_snap     = ch_snap,
        days        = 30
    )

    from utils.estimate_daily_subscribers import estimate_daily_subscribers
    estimated_daily_subscribers = estimate_daily_subscribers(ch_snap, spread_change_df) # ['Date', 'Estimated Subscribers'] 
    st.header("구독자 수 추이📈")
    render_estimated_subscribers_chart(estimated_daily_subscribers)
    #───────────────────────────────────────────────────────────


    # Shorts vs Long-form 평균 조회수
    st.header("누적 평균 조회수👑")

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
                ">Long-form</span> 공개 이후 일자별 기대 조회수
                """, unsafe_allow_html=True)
        # st.metric(label="Long-form 평균 조회수", value=f"{int(avg_views(ch_df, 10, False)):,}")
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
        ">Shorts</span> 공개 이후 일자별 기대 조회수
        """, unsafe_allow_html=True)
        # st.metric(label="Shorts 평균 조회수", value=f"{int(avg_views(ch_df, 10, True)):,}")
        render_avg_views_table(short_metrics)
        render_avg_views_line_chart(result_S, "")
    
    #─────────────────────────────────────────────────────────── gainscore 계산 시작
    # 1) per-video Gain Score 계산
    #    반환값: DataFrame with columns ['video_id','gain_score']
    video_gain_df = compute_video_gain_scores(
        channel_df   = ch_df,
        ch_snap = ch_snap,
        estimated_daily_subscribers = estimated_daily_subscribers,
        end_subs     = latest_subs,
        total_view  = total_view,
        c            = 100.0,
        days         = 14
    )

    # 1.5) subscriber_contrib 계산 (채널별 last_run_date 로 관리)
    today_date = datetime.date.today()
    today_str = today_date.isoformat()
    last_run = channel_meta.get("last_run_date")

    if last_run != today_str:
        if last_run is None:
            initial_batch(ch_df, result_L, avg_daily_increase)      # 초기 계산 with external avg_daily_increase
        else:
            st.write(f"[DEBUG] Performing incremental_update for {channel_id}")
            incremental_update(ch_df, result_L)          # 일일 업데이트
    else:
        st.write(f":white_check_mark: Channel {channel_id} subs_contrib already updated today.")

    # CSV에서 갱신된 subs_contrib 불러오기
    subs_df = pd.read_csv(SUBS_FILE)             # 전체 채널 # columns: video_id, subs_contrib
    subs_df_ch = subs_df[subs_df["channel_id"] == channel_id]


    # 3) 기본이 계산
    final_score_df = compute_gain_score(
        ch_df=ch_df,
        ch_snap=ch_snap,
        days=30
    )
    # ──────────────────────────────────────────────────────────

    # 최근 영상 Expander
    st.header("영상 퍼포먼스 분석 📹")

    # 1) 롱폼/숏폼 필터링 탭
    tab_longs, tab_shorts, tab_all = st.tabs(["롱폼", "쇼츠", "전체영상"])
    
    # 2) 탭별 데이터 필터링 함수
    def filter_by_tab(df, tab_name):
        if tab_name == "쇼츠":
            return df[df['is_short'] == True]
        elif tab_name == "롱폼":
            return df[df['is_short'] == False]
        return df

    for tab_name, tab in zip(["롱폼", "쇼츠", "전체영상"], [tab_longs, tab_shorts, tab_all]):
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

            # update_video['published_at_dt'] = pd.to_datetime(update_video['published_at_dt'], errors='coerce')

            if sort_option == "최신순":
                update_video = update_video.sort_values('published_at', ascending=False) ##_dt필요한가?
            elif sort_option == "조회수순":
                update_video = update_video.sort_values('view_count', ascending=False)
            else:  # 기여도순
                update_video = update_video.sort_values('gain_score', ascending=False)
            
            #여기에 칼럼 업데이트-------------------------------------------------------
            map_L = result_L.set_index('day')['cumulative_view_count'].to_dict()
            map_S = result_S.set_index('day')['cumulative_view_count'].to_dict()
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