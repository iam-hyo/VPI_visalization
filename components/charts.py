# components/charts.py
import streamlit as st
import pandas as pd

def draw_pie_chart(labels, values, title=""):
    df = pd.DataFrame({"label": labels, "value": values})
    st.subheader(title)
    st.pyplot(__import__('matplotlib.pyplot').pyplot.figure(figsize=(4,4)))
    fig = __import__('matplotlib.pyplot').pyplot.gcf()
    fig.clear()
    ax = fig.add_subplot(111)
    ax.pie(df['value'], labels=df['label'], autopct='%1.1f%%')
    st.pyplot(fig)

def draw_line_chart(x, y, title=""):
    st.subheader(title)
    st.line_chart(data={title: y}, x=x)
