import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="유튜브 채널 분석", layout="wide")
st.title("📈 YouTube 채널 영상 분석 대시보드")

# 데이터 로드
DATA_PATH = "data/processed_data_v2.csv"
try:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
except Exception as e:
    st.error(f"CSV 로딩 실패: {e}")
    st.stop()

# 날짜 변환
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
df['published_at'] = df['published_at'].dt.tz_localize(None)

# 최근 7일 기준 필터링
df = df.sort_values('timestamp')
latest_date = df['timestamp'].max()
days_window = 7
first_date = latest_date - pd.Timedelta(days=days_window - 1)
df_last = df[df['timestamp'] >= first_date]

# 카테고리별 탭 구성
categories = sorted(df_last['category'].unique())
category_tabs = st.tabs(categories)

for cat_tab, category in zip(category_tabs, categories):
    with cat_tab:
        st.header(f"🌟 카테고리: {category}")

        cat_data = df_last[df_last['category'] == category]
        channels = cat_data['channel_id'].unique()
        channel_tabs = st.tabs([
            f"{cat_data[cat_data['channel_id'] == ch]['channel_handle'].iloc[0]}" for ch in channels
        ])

        for ch_tab, ch_id in zip(channel_tabs, channels):
            with ch_tab:
                channel_data = cat_data[cat_data['channel_id'] == ch_id].copy()
                if channel_data.empty:
                    continue

                ch_handle = channel_data['channel_handle'].iloc[0]

                # 구독자수 분석
                subs_by_day = channel_data.groupby('timestamp')['subscriber_count'].last().sort_index()
                subs_by_day = subs_by_day.interpolate(method='linear')

                days_elapsed = (subs_by_day.index[-1] - subs_by_day.index[0]).days or 1
                subs_latest = int(subs_by_day.iloc[-1])
                subs_initial = int(subs_by_day.iloc[0])
                subs_gain = subs_latest - subs_initial
                subs_daily_gain = subs_gain / days_elapsed
                subs_gain_rate = subs_gain / (subs_latest or 1)

                st.subheader(f"🕵️‍♂️ 채널: {ch_handle} ({days_elapsed}일 기준)")
                st.write(f"최근 {days_elapsed}일간 구독자수 증가: {subs_gain:+,}명")
                st.write(f"일평균 증가량: {subs_daily_gain:.2f}명/일")
                st.write(f"증가율: {subs_gain_rate:.2%}")

                st.line_chart(subs_by_day.rename("구독자수"))

                # 영상 분석 섹션
                st.markdown("---")
                st.subheader("🔍 영상 분석")

                latest_data = channel_data[channel_data['timestamp'] == channel_data['timestamp'].max()].copy()
                initial_data = channel_data[channel_data['timestamp'] == channel_data['timestamp'].min()]
                initial_views = {vid: v for vid, v in zip(initial_data['video_id'], initial_data['view_count'])}

                view_gain = {}
                for vid, vcount in zip(latest_data['video_id'], latest_data['view_count']):
                    init = initial_views.get(vid, 0)
                    view_gain[vid] = max(vcount - init, 0)

                total_gain = sum(view_gain.values())
                latest_data['구독자 기여도'] = latest_data['video_id'].apply(
                    lambda vid: (view_gain.get(vid, 0) / total_gain) * subs_gain if total_gain else 0)
                latest_data['구독자 기여도'] = latest_data['구독자 기여도'].round(1)

                # 파이차트
                st.write("🎂 영상별 구독자 기여도")
                if latest_data['구독자 기여도'].sum() > 0:
                    pie_fig = px.pie(latest_data, names='video_title', values='구독자 기여도',
                                     title='영상별 구독자 기여도')
                else:
                    pie_fig = px.pie(latest_data, names='video_title', values='view_count',
                                     title='기여도 데이터 없음: 영상별 조회수 비율')
                st.plotly_chart(pie_fig)

                # 영상 필터링 옵션
                filter_opt = st.radio("영상 필터", ["전체", "숏폼", "롱폼"], horizontal=True, key=f"filter_{ch_id}")
                sort_opt = st.selectbox("정렬 기준", ["기여도순", "최신 순", "오래된 순"], key=f"sort_{ch_id}")

                filtered = latest_data.copy()
                if filter_opt == "숏폼":
                    filtered = filtered[filtered['is_short'] == True]
                elif filter_opt == "롱폼":
                    filtered = filtered[filtered['is_short'] == False]

                if sort_opt == "기여도순":
                    filtered = filtered.sort_values("구독자 기여도", ascending=False)
                elif sort_opt == "최신 순":
                    filtered = filtered.sort_values("published_at", ascending=False)
                else:
                    filtered = filtered.sort_values("published_at", ascending=True)

                st.write(f"최근 영상 {len(filtered)}개")

                for i, (_, row) in enumerate(filtered.iterrows()):
                    title = row['video_title']
                    pub_date_raw = row['published_at']

                    try:
                        pub_date = pd.to_datetime(pub_date_raw, errors='coerce')
                    except:
                        pub_date = pd.NaT

                    if pd.notnull(pub_date):
                        pub_date = pub_date.tz_localize(None)

                    if pd.notnull(pub_date):
                        days_since = (datetime.now() - pub_date).days
                        d_string = f"D+{days_since}"
                    else:
                        days_since = None
                        d_string = "D+?"

                    st_expander_label = f"📺 {title} ({d_string})"
                    with st.expander(st_expander_label):
                        st.write(f"영상 ID: `{row['video_id']}`")
                        if pd.notnull(pub_date):
                            st.write(f"업로드 일시: {pub_date.strftime('%Y-%m-%d %H:%M')} ({d_string})")
                        else:
                            st.write("업로드 일시: 알 수 없음")
                        st.write(f"조회수: {row['view_count']:,}")
                        st.write(f"구독자 기여도: {row['구독자 기여도']:.1f}명")

                st.markdown("---")
