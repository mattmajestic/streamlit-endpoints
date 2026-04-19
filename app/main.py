import streamlit as st

st.set_page_config(
    page_title="Streamlit + Starlette",
    page_icon="https://github.com/mattmajestic/majesticcoding.com/blob/main/static/img/mc-logo.png?raw=true",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/fastf1_demo.py", title="FastF1 Analytics", icon="🏎️"),
    st.Page("pages/api_demo.py", title="API Demo", icon="🔌"),
])
pg.run()
