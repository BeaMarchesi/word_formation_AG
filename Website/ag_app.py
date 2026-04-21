import streamlit as st
from style import apply_style
apply_style()
from utils import *

render_top_right_logos([
    {'path': 'Website/Images/logo_larl_rosso.png',       'url': 'https://linguisticapavia.cdl.unipv.it', 'alt': 'LARL'},
    {'path': 'Website/Images/90690393.png', 'url': 'https://www.unipv.it',                  'alt': 'UniPV'},
])

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