import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(page_title="유튜브 채널 7일간 구독자 분석", layout="wide")

# 앱 제목
st.title("유튜브 채널 7일간 구독자 증가 분석 대시보드")

# 데이터 소스 선택: CSV 또는 JSON
data_option = st.radio("데이터 소스 선택:", ["CSV (processed_data.csv)", "JSON (raw_data.json)"], index=0)
data_path = "data/processed_data.csv" if data_option.startswith("CSV") else "data/raw_data.json"

# 데이터 불러오기
try:
    if data_path.endswith(".csv"):
        df = pd.read_csv(data_path)
    else:
        df = pd.read_json(data_path)
except Exception as e:
    st.error(f"데이터 로딩 실패: {data_path} 에러: {e}")
    st.stop()

# timestamp 컬럼을 datetime 형식으로 변환
if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# 최신 날짜 기준 최근 7일 데이터 필터링
df = df.sort_values('timestamp')
if len(df['timestamp'].unique()) >= 7:
    last_date = df['timestamp'].max()
    first_date = last_date - pd.Timedelta(days=6)
    df_last7 = df[df['timestamp'] >= first_date]
else:
    df_last7 = df

# 카테고리별 탭 생성
categories = sorted(df_last7['category'].unique())
category_tabs = st.tabs(categories)

# 카테고리별 분석
for cat_tab, category in zip(category_tabs, categories):
    with cat_tab:
        st.header(f"카테고리: {category}")

        # 해당 카테고리의 데이터 필터링
        cat_data = df_last7[df_last7['category'] == category]

        # 채널별 탭 생성
        channels = cat_data['channel_id'].unique()
        channel_tabs = st.tabs([
            f"{cat_data[cat_data['channel_id'] == ch]['channel_handle'].iloc[0]}" for ch in channels
        ])

        # 채널별 분석
        for ch_tab, ch_id in zip(channel_tabs, channels):
            with ch_tab:
                channel_data = cat_data[cat_data['channel_id'] == ch_id]
                if channel_data.empty:
                    continue

                # 채널명 가져오기
                ch_handle = channel_data['channel_handle'].iloc[0]

                # timestamp 정렬
                channel_data['timestamp'] = pd.to_datetime(channel_data['timestamp'])
                channel_data = channel_data.sort_values(['timestamp', 'video_id'])

                # 구독자수 추이 계산 (중복 제거: 동일날짜 여러영상 있을 때 '마지막 데이터' 사용)
                subs_by_day = channel_data.groupby('timestamp')['subscriber_count'].last()

                # 결측치 선형보간
                subs_by_day = channel_data.groupby('timestamp')['subscriber_count'].last()
                subs_by_day = subs_by_day.interpolate(method='linear')

                # 최신 구독자수와 초기 구독자수 계산
                subs_latest = int(subs_by_day.iloc[-1])
                subs_initial = int(subs_by_day.iloc[0])
                subs_gain_7d = subs_latest - subs_initial

                # 채널 헤더
                st.subheader(f"채널: {ch_handle} (ID: {ch_id})")
                st.write(f"최근 7일간 구독자수 증가: {subs_gain_7d:+,}")
                
                st.write(f"최신 구독자수: {subs_latest:,}")
                st.write(f"초기 구독자수: {subs_initial:,}")

                # 디버깅
                # st.write(f"🛠️ [디버깅] 채널 데이터 샘플 ({ch_handle})")
                # st.write(channel_data[['timestamp', 'subscriber_count']].drop_duplicates().sort_values('timestamp'))

                # 채널 정보 섹션
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.write("📈 **구독자수 추이 (7일간)**")
                    st.line_chart(subs_by_day)

                with col2:
                    # 영상별 기여도 계산
                    latest_date = channel_data['timestamp'].max()
                    latest_data = channel_data[channel_data['timestamp'] == latest_date]

                    initial_date = channel_data['timestamp'].min()
                    initial_data = channel_data[channel_data['timestamp'] == initial_date]
                    initial_views = {vid: v for vid, v in zip(initial_data['video_id'], initial_data['view_count'])}

                    view_gain = {}
                    for vid, vcount in zip(latest_data['video_id'], latest_data['view_count']):
                        initial_v = initial_views.get(vid, 0)
                        gain = vcount - initial_v
                        view_gain[vid] = gain if gain >= 0 else 0

                    total_view_gain = sum(view_gain.values())

                    videos = latest_data[['video_id', 'view_count']].copy()
                    videos['구독자 기여도'] = 0.0
                    if total_view_gain > 0 and subs_gain_7d != 0:
                        for idx, row in videos.iterrows():
                            vid = row['video_id']
                            contrib = (view_gain.get(vid, 0) / total_view_gain) * subs_gain_7d
                            videos.at[idx, '구독자 기여도'] = contrib
                    videos['구독자 기여도'] = videos['구독자 기여도'].round(1)

                    st.write("🥧 **영상별 구독자 기여도 (Pie Chart)**")
                    if videos['구독자 기여도'].sum() > 0:
                        pie_fig = px.pie(videos, names='video_id', values='구독자 기여도',
                                         title='영상별 구독자 기여도')
                    else:
                        pie_fig = px.pie(videos, names='video_id', values='view_count',
                                         title='구독자 기여도 데이터 없음: 영상별 조회수 비율')
                    st.plotly_chart(pie_fig)

                # Top10 영상 리스트 출력
                st.write("🎬 **Top 10 영상 리스트 (클릭시 상세 그래프 표시)**")
                videos = videos.sort_values('view_count', ascending=False).head(10)
                for idx, row in videos.iterrows():
                    vid = row['video_id']
                    vcount = row['view_count']
                    contrib = row['구독자 기여도']

                    with st.expander(f"영상 ID: {vid} | 조회수: {vcount:,} | 구독자 기여도: {contrib:.1f}"):
                        st.write(f"영상 ID: {vid}")
                        st.write(f"조회수: {vcount:,}")
                        st.write(f"구독자 기여도: {contrib:.1f}")

                        # ✅ 최종 코드 삽입
                        # subs_by_day와 video_views_by_day 정렬
                        subs_by_day = subs_by_day.sort_index()
                        video_data = channel_data[channel_data['video_id'] == vid]
                        video_views_by_day = video_data.groupby('timestamp')['view_count'].max().sort_index()

                        # 디버깅 출력
                        st.write("🔍 subs_by_day:")
                        st.write(subs_by_day)
                        st.write("🔍 video_views_by_day:")
                        st.write(video_views_by_day)

                        # index outer join으로 합치기
                        graph_df = pd.concat([subs_by_day, video_views_by_day], axis=1)
                        graph_df.columns = ['구독자수', '영상 조회수']

                        # 그래프 출력
                        st.line_chart(graph_df)

                        


                      

                # 채널별 구분선
                st.markdown("---")
