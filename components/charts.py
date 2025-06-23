# components/charts.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def draw_pie_chart(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str = "",
    date_col: str = None,
    latest_n: int = None,
):
    """
    df         : 입력 DataFrame (예: contrib_df)
    label_col  : 파이 차트의 레이블로 사용할 컬럼명 (예: 'title')
    value_col  : 값으로 사용할 컬럼명 (예: 'contribution' 또는 'view_count')
    title      : 차트 제목
    date_col   : 최신 n개를 뽑기 위한 날짜 컬럼명 (예: 'publish_date')
    latest_n   : date_col 기준으로 남길 최신 row 개수 (예: 10)
    """
    st.write(df)
    # 1) 최신 n개만 추출
    if date_col and latest_n:
        df = df.sort_values(date_col, ascending=False).head(latest_n)

    labels = df[label_col].astype(str).tolist()
    values = df[value_col].tolist()

    # 2) 값이 전부 0이면 view_count 비례로 재계산
    if sum(values) == 0 and 'view_count' in df.columns:
        total = df['view_count'].sum()
        if total > 0:
            values = (df['view_count'] / total).tolist()

    # 3) 유의미한 값 체크
    if sum(values) == 0:
        st.subheader(title)
        st.warning("표시할 데이터가 없습니다.")
        return

    # 4) 차트 그리기
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(values, labels=labels, autopct='%1.1f%%')
    ax.set_title(title)
    ax.axis('equal')

    # 5) Streamlit 출력
    st.subheader(title)
    st.pyplot(fig)

def draw_line_chart(df: pd.DataFrame, x: str, y: str, title: str):
    st.subheader(title)
     # 1) 필요한 컬럼만 복사
    df_plot = df[[x, y]].copy()
    
    # 2) x축이 문자열이라면 datetime으로 변환
    df_plot[x] = pd.to_datetime(df_plot[x])
    
    # 4) x축 컬럼을 인덱스로 설정
    df_plot = df_plot.set_index(x)
    
    # 5) line_chart: 인덱스를 x축으로, y 컬럼을 y축으로 그리기
    st.line_chart(df_plot[y], use_container_width=True)

def render_avg_views_table(df_metrics):  # 일차별 평균조회수 테이블
    """
    df_metrics: ['day', '평균 조회수']
    """
    st.dataframe(df_metrics)

def render_avg_views_line_chart(df_metrics, title: str): # 일차별 꺾은선 그래프
    """
    df_metrics: ['day', '평균 조회수']
    """
    # st.subheader(title)
    # index를 day로 설정하고 line_chart 호출
    st.line_chart(
        df_metrics.set_index('day')['avg_view_count'],
        use_container_width=True
    )