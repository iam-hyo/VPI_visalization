# pages/2_ChannelDetail.py
import streamlit as st
import json
import streamlit.components.v1 as components
from streamlit.components.v1 import html
from utils.data_loader import load_processed_data, load_channel_meta
from utils.metrics import (
    get_subscriber_metrics, avg_views, moving_average_views,
    calculate_contribution, video_contribution_by_type,
    avg_view_by_days_since_published, format_korean_count, parse_published_at
)
from components.sidebar import render_sidebar
from components.charts import draw_line_chart, draw_pie_chart, render_avg_views_table, render_avg_views_line_chart
from components.expander import render_video_expander
from components.html_expander import summary_card, detail_expander
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

    ch_df['published_at_dt'] = parse_published_at(ch_df['published_at'])
    ch_df['day_since_pub'] = (ch_df['timestamp'] - ch_df['published_at_dt']).dt.days + 1 #공개 후 경과일 계산 (1일 차부터)

    # st.write(end, start, channel_id, growth, daily_avg)
    profile_url = channel_meta[channel_id]["profile_image"]
    img_base64 = img_url_to_base64(profile_url)

    #==========================UI랜더링=========================
    html_code = f"""
    <div class="yt-profile">
        <img class="channel-img" src="data:image/jpeg;base64,{img_base64}" alt="채널 이미지">
        <div class="channel-info">
            <div class=Name-tag>
                <h2 class="channel-name">{channel_meta[channel_id]["channel_title"]}</h2>
                <p class="handle">{channel_meta[channel_id]["handle"]}</p>
                <!--<p class="channel-subs">{ch_df['subscriber_count'].iloc[-1]}</p>-->
            </div>
            <p class="category">{ch_df['category'].iloc[-1]}</p>
        </div>
    </div>

    <style>

    .category {{
        font-size: 15px;
        width: min-content;
        color: #444;
        padding: 4px 10px;
        background-color: #096b6b;
        border-radius: 8px;
    }}

    .yt-profile {{
        display: flex;
        align-items: center;
        background-color: #f9f9f9;
        border-radius: 12px;
        padding: 0px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }}

    .Name-tag{{
        display: flex;
        gap: 10px;
    }}
    .channel-img {{
        width: 120px;
        height: 120px;
        object-fit: cover;
        margin-right: 20px;
        border: 2px solid #ccc;
        border-radius: 10px;
    }}

    .channel-info {{
        flex: 1;
    }}

    .channel-name {{
        margin: 0;
        font-size: 32px;
        font-weight: bold;
        color: #222;
    }}

    .handle {{
        font-size: 16px;
        color: #777;
    }}

    
    </style>
    """
    components.html(html_code, height=160)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("구독자 수", f"{end:,}명") 
    with col2:
        st.metric("총 영상 수", f"{channel_meta[channel_id]['video_count']:,}개")
    formated_total_view = format_korean_count(channel_meta[channel_id]['total_view_count'])
    with col3:
        st.metric("총 조회수", f"{formated_total_view}회")
    with col4:
        st.metric("구독자 증가수", f"{growth:,}명")
    with col5:
        st.metric("30일 일평균 구독자 증가량", f"{daily_avg:,.1f}명")
    

    # Shorts vs Long-form 평균 조회수
    st.write("---")
    st.header("영상 통계량👑")
    col1, col2 = st.columns(2)
    with col1: # 롱폼
        long_metrics, result_L = avg_view_by_days_since_published(
            ch_df,
            max_days=10,
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
            max_days=10,
            is_short=True
        )
        st.markdown("#### :blue-badge[Short Form] 공개 이후 평균 조회수")
        st.metric(label="Shorts 평균 조회수", value=f"{int(avg_views(ch_df, 10, True)):,}")
        render_avg_views_table(short_metrics)
        render_avg_views_line_chart(result_S, "")

    # 기여도 파이차트
    # contrib_df = calculate_contribution(ch_df)
    # draw_pie_chart(
    #     df=contrib_df,
    #     label_col="title",
    #     value_col="contribution",
    #     date_col="published_at",
    #     latest_n=10,
    #     title="최신 10개 영상별 기여도"
    # )
    # type_df = video_contribution_by_type(ch_df)
    # draw_pie_chart(type_df["type"], type_df["contribution"], "Shorts vs Long")

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
            # 4-1) 필터링
            sub = filter_by_tab(ch_df, tab_name)

            # 4-2) 최신 스냅샷 기준으로 video_id별 최신 row만
            update_video = (sub.sort_values('timestamp', ascending=False)
                            .drop_duplicates(subset='video_id', keep='first'))
            # 3) 정렬 기준 선택
            col1, col2 = st.columns([3,1])
            # 4-4) 총 영상 개수 표시
            col1.markdown(f"**총 영상개수: {len(update_video):,}개**")
            sort_option = col2.selectbox("정렬 순서",["최신순", "조회수순", "기여도순"],index=0, key=f"sort-{tab_name}")

             # 4-3) 정렬 적용
            if sort_option == "최신순":
                update_video = update_video.sort_values('published_at', ascending=False)
            elif sort_option == "조회수순":
                update_video = update_video.sort_values('view_count', ascending=False)
            else:  # 기여도순
                update_video = update_video.sort_values('contribution', ascending=False)
            
            
            for _, row in update_video.iterrows():
                days_since_pub = row['day_since_pub']

                # 3) expected_views 뽑기
                metrics_df = result_S if row['is_short'] else result_L
                exp_row = metrics_df.loc[metrics_df['day']==days_since_pub, 'avg_view_count']
                expected_views = int(exp_row.iloc[0]) if not exp_row.empty else 0

                views_str      = f"{row.view_count:,}회"
                pub_str        = row.published_at_dt.strftime("%Y-%m-%d")
                days_since_pub = row.day_since_pub
                # expected_str   = f"{int(row.expected_views):,}회"
                badge          = "Shorts" if row.is_short else "Long-form"
                
                # 차트 HTML 생성 (Chart.js 예시)
                chart_id = f"chart-{row.video_id}"
                labels   = result_L['day'].tolist() if not row.is_short else result_S['day'].tolist()
                values   = result_L['avg_view_count'].tolist() if not row.is_short else result_S['avg_view_count'].tolist()
                chart_html = f"""
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <canvas id="{chart_id}" style="width:100%;height:300px;"></canvas>
                <script>
                new Chart(
                document.getElementById('{chart_id}').getContext('2d'),
                {{
                    type: 'line',
                    data: {{ labels: {labels}, datasets:[{{ label:'평균 조회수', data:{values}, fill:false, tension:0.3 }}] }},
                    options: {{ scales: {{ y:{{ beginAtZero:true }} }} }}
                }}
                );
                </script>
                """

                # 1) 요약 HTML
                summary_card(
                    thumbnail_url  = row.thumbnail_url,
                    title          = row.video_title,
                    badge          = badge,
                    views_str      = views_str,
                    pub_str        = pub_str,
                    days_since_pub = days_since_pub,
                    expected_str   = expected_views
                )

                vid = row['video_id']
                video_snapshots = ch_df[ch_df['video_id'] == vid].copy()

                # 2) ‘자세히 보기’ Expander
                detail_expander(
                    snapshot_df   = video_snapshots,
                    metrics_df    = metrics_df,
                    video_id      = vid,
                    like_count    = row.get('like_count'),
                    comment_count = row.get('comment_count'),
                )
if __name__ == "__main__":
    main()
