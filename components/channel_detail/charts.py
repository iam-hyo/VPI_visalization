# components/charts.py
import streamlit as st
import pandas as pd
import plotly.express as px

def render_avg_views_table(df_metrics):  # 일차별 평균조회수 테이블
    """
    df_metrics: ['day', '평균 조회수']
    """
    df_metrics = df_metrics.map(lambda x: f"{int(x):,}")
    st.dataframe(df_metrics)

def render_avg_views_line_chart(df_metrics, title: str = ""):
    # 전체 30일치 데이터
    fig = px.line(
        df_metrics,
        x='day',
        y='avg_view_count',
        markers=True
    )

    # tick 값과 레이블 생성 (예: 1일,2일,…,30일)
    tickvals = list(df_metrics['day'])
    ticktext = [f"{int(d)}일" for d in tickvals]

    # 레이아웃 업데이트
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext,
            range=[1, 10],               # 초기 뷰: 1~10일
            rangeslider=dict(visible=True),
            title=None                   # x축 제목 제거
        ),
        yaxis=dict(
            tickformat=',.0f',           # 천 단위 콤마 (예: 200,000)
            range=[0, df_metrics['avg_view_count'].max() * 1.1],
            title=None                   # y축 제목 제거
        ),
        margin=dict(l=40, r=20, t=20, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

def render_estimated_subscribers_chart(df: pd.DataFrame) -> None:
    # Plotly Express를 사용해 일별 추정 구독자수를 라인 차트로 렌더링 (매일 포인트 포함)

    df_plot = df.copy()
    df_plot['Date'] = pd.to_datetime(df_plot['Date'])

    # y축 범위: 실제 최소/최대값
    y_min = df_plot['Estimated Subscribers'].min()
    y_max = df_plot['Estimated Subscribers'].max()

    # 라인 차트 생성 (매일 포인트 표시)
    fig = px.line(
        df_plot,
        x='Date',
        y='Estimated Subscribers',
        markers=True,
        title=''  # 제목 없음
    )
    # x축: MM월DD일 포맷, 라벨 각도
    fig.update_xaxes(
        tickformat='%m월%d일',
        tickangle=0,
        title_text=''
        )
    # y축: 범위 설정 및 제목
    fig.update_yaxes(
        range=[y_min, y_max],
        title_text='구독자 수',
        tickformat=',.0f',
    )
    # 범례 제거
    fig.update_layout(showlegend=False)

    st.plotly_chart(fig, use_container_width=True)


