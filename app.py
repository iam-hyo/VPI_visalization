import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
 
## 데이터 불러오기
data = pd.read_csv('data/processed_data_v2.csv')
###################
def debug_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        st.write("▶ Raw JSON snippet:", raw[:200])
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")

# 어디든 호출해서 경로를 맞춰 보세요
debug_json("data/channel_meta.json")


################################
col1, col2 = st.columns([2, 3])
with col1:
    st.metric(label="측정치 1", value=123)
    st.caption("이는 측정치 1에 대한 추가 정보입니다.")
with col2:
    st.metric(label="측정치 2", value=456)
    st.caption("이는 측정치 2에 대한 추가 정보입니다.")


    ############

col1, col2 = st.columns(2)
with col1:
    if st.button("나를 클릭하세요!"):
        st.write("버튼이 클릭되었습니다!")
with col2:
    if st.button("나를 클릭하지 마세요!"):
        st.write("버튼이 클릭되었습니다!")


with st.container():
    st.write("이것은 외부 컨테이너입니다.")
    with st.container():
        st.write("이것은 내부 컨테이너입니다.")

with st.expander("클릭하여 펼치기"):
    st.write("숨겨진 콘텐츠")

    
col1, col2 = st.columns(2)
with col1:
    st.line_chart([0, 1, 2, 3, 4])
with col2:
    st.line_chart([4, 3, 2, 1, 0])

# width와 height 인자 사용 예시
data = [1,2,3,4,5,6]

column1, column2 = st.columns(2)
with column1:
    st.bar_chart(data, width=900, height=200)
with column2:
    st.line_chart(data, width=300, height=600)


# ===============
from pyparsing import empty
import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image

st.set_page_config(layout="wide")
empty1,con1,empty2 = st.columns([0.3,1.0,0.3])
empyt1,con2,con3,empty2 = st.columns([0.3,0.5,0.5,0.3])
empyt1,con4,empty2 = st.columns([0.3,1.0,0.3])
empyt1,con5,con6,empty2 = st.columns([0.3,0.5,0.5,0.3])

with empty1 :
        empty() # 여백부분1
with con1 :
    st.bar_chart(data, width=900, height=200)

with con2 :
    st.bar_chart(data, width=900, height=200)
    st.bar_chart(data, width=900, height=200)
    st.bar_chart(data, width=900, height=200)
with con3 :
    st.dataframe(data)