import streamlit as st
import pandas as pd
from utils.data_loader import load_processed_data, load_channel_meta
from components.channel_card import render_channel_card

st.set_page_config(
    page_title="VPI",
    page_icon="📺",
    layout="wide",                    # 필요에 따라 'centered'로 바꿔도 됩니다
    initial_sidebar_state="collapsed" # 'collapsed', 'expanded', 또는 'auto'
)
# 데이터 불러오기
df = load_processed_data()
channel_meta = load_channel_meta()

# 📌 채널별 통계 계산
latest = df.groupby('channel_id').last()
earliest = df.groupby('channel_id').first()

# 🔍 카테고리 설정
categories = ["전체"] + sorted(df['category'].unique())


# 정렬 순서 정의
subs_diff = latest['subscriber_count'] - earliest['subscriber_count']
avg_views = df.groupby('channel_id')['view_count'].mean()
short_ratio = df.groupby('channel_id')['is_short'].mean()
category_map = df.groupby('channel_id')['category'].last()

sort_column_map = {
    "구독자순": latest['subscriber_count'],
    "구독자 급상승": subs_diff,
    "평균 조회수": avg_views,
    "Shorts 비율": short_ratio
}

#=================== Page 랜더링 =====================


non1, main, non2 = st.columns([1, 10, 1])
with main :
        
    st.metric(value="📺VPI", label="Vido Performence Indicater")
    st.caption("가장 강력한 유튜브 분석 도구")

    tabs = st.tabs(categories)

    def render_channels_for(category: str):
        """
        주어진 카테고리(category)에 맞춰
        sort_series 순서대로 채널 카드를 렌더링합니다.
        """
        for channel_id in sort_series.index:
            meta = channel_meta.get(channel_id, {})
            if not meta:
                continue

            # 카테고리 필터링
            cat = meta.get("category", "")
            if category != "전체" and cat != category:
                continue

            stats = {
                "subs_diff": subs_diff.get(channel_id, 0),
                "avg_views": avg_views.get(channel_id, 0),
                "short_ratio": short_ratio.get(channel_id, 0.0)
            }
            render_channel_card(channel_id=channel_id, meta=meta, stats=stats)

    for tab, category in zip(tabs, categories):
        with tab:
            col1, col2 = st.columns([4, 1])
            # 여기에 카테고리 필터링 결과 개수 반환
            if category == "전체":
                filtered_ids = list(channel_meta.keys())
            else:
                filtered_ids = [
                cid 
                for cid, meta in channel_meta.items() 
                if meta.get("category", "") == category
            ]
            count = len(filtered_ids)
            col1.metric(label=f"결과 {count}명", value="Youtuber List")
            # col1.html(f"""
            #         <style>
            #             div{{margin: 5px 0px 0 0;}}
            #             h1{{display: inline;}}
            #             p{{display: inline; color: #666;}}
            #         </style>
            #         <div><h1>Youtuber List</h1> <p>{count}명</p></div>
            #         """)
            with col2 :
                sort_key = st.selectbox(
                    "정렬 기준", ["구독자순", "구독자 급상승", "평균 조회수", "Shorts 비율"],
                    key=f"sort_{category}",
                    index=1
                    )
            sort_series = sort_column_map[sort_key].sort_values(ascending=False)

            
            # 4) 결과 개수 함께 출력
            
            render_channels_for(category)


