import streamlit as st

st.set_page_config(
    page_title="Streamlit + Starlette",
    page_icon="🚀",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/fastf1_demo.py", title="FastF1 Analytics", icon="🏎️"),
    st.Page("pages/api_demo.py", title="API Demo", icon="🔌"),
])
pg.run()
