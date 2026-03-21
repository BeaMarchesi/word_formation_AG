import streamlit as st
from style import apply_style
apply_style()
from utils import *

render_top_right_logos([
    {'path': 'Website/Images/logo_larl_rosso.png',       'url': 'https://linguisticapavia.cdl.unipv.it', 'alt': 'LARL'},
    {'path': 'Website/Images/90690393.png', 'url': 'https://www.unipv.it',                  'alt': 'UniPV'},
])

home = st.Page("home_page.py", title="Home",default=True)
entry = st.Page("entry_search.py", title="Search by entry")
derivation = st.Page("derivation_search.py", title="Search by composition or derivation")

pg = st.navigation([home, entry, derivation])

pg.run()

