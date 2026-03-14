import streamlit as st
from style import apply_style
apply_style()
from utils import *

render_top_right_logos([
    {'path': 'Website/Images/logo_larl_rosso.png',       'url': 'https://linguisticapavia.cdl.unipv.it', 'alt': 'LARL'},
    {'path': 'Website/Images/90690393.png', 'url': 'https://www.unipv.it',                  'alt': 'UniPV'},
])

pages = {
    "": [
        st.Page("home_page.py", title="Home", default=True)
    ],

    "Basic search": [
            st.Page("lemma.py", title="Search by lemma"),
            st.Page("POS+affix.py",  title="Search by part of speech and affix"),
        ],

    "Search by composition or derivation": [
        st.Page("lemma+POS.py", title="Search by lemma and part of speech"),
        st.Page("lemma+affix.py", title="Search by lemma and affix"),
        st.Page("conversion.py", title="Search by conversion"),
    ],
}

pg = st.navigation(pages)
pg.run()

