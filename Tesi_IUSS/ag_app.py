import streamlit as st
from style import apply_style
apply_style()
from utils import *


pages = {
    "Home": [
        st.Page("home_page.py", title="About the resource"),
        st.Page("team.py", title="Team"),
    ],
    "Query the database": [
        st.Page("entry_search.py", title="Search by entry"),
        st.Page("derivation_search.py", title="Search by derivation or composition"),
    ],
}

pg = st.navigation(pages)
pg.run()