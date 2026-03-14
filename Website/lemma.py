import unicodedata
import re

import streamlit as st
import pandas as pd

from utils import *
from style import apply_style

apply_style()

CSV_PATH = 'kb.csv'
LOGO_PATH = 'Website/Images/logo_larl_rosso.png'
LOGO_LINK = 'https://www.facebook.com/groups/251278298330026/?locale=it_IT'


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    from ast import literal_eval
    return pd.read_csv(CSV_PATH, converters={'etymology_raw': literal_eval, 'prefix': literal_eval})


@st.cache_data(show_spinner=False)
def build_lookup(lemma_raw: pd.Series, betacode_raw: pd.Series) -> dict:
    """Build lookup dict by passing only Series (not full DataFrame) to avoid
    cache hashing errors caused by list-typed columns like prefix/etymology_raw."""
    lookup: dict[str, list[int]] = {}
    for idx in lemma_raw.index:
        val = lemma_raw[idx]
        if isinstance(val, str):
            lookup.setdefault(val, []).append(idx)
        val = betacode_raw[idx]
        if isinstance(val, str):
            lookup.setdefault(val, []).append(idx)
    return lookup


@st.cache_data(show_spinner=False)
def build_options(query_lemmas: pd.Series) -> list[str]:
    """Return sorted display labels, safely dropping NaN floats."""
    return sorted(
        [v for v in query_lemmas if isinstance(v, str)],
        key=str.casefold,
    )


# ── Page layout ───────────────────────────────────────────────────────────────

st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)
st.title("Word Formation Ancient Greek", text_alignment = 'center')
st.divider()
st.header("Search by lemma", text_alignment = 'center')

kb = load_data()
lookup = build_lookup(kb['lemma_raw'], kb['lemma_betacode_raw'])
options = build_options(kb['query_lemmas'])

search_lemma = st.selectbox(
    'Search',
    options=options,
    key='lemma_selectbox',
    index=None,
    accept_new_options=True,
    help='Both inputs in the Ancient Greek alphabet and in betacode are accepted.\n'
         'Inputs in the Ancient Greek alphabet must have the correct diacritics.\n'
         'Inputs in betacode must be stripped of any diacritics.',
)

_, col, _ = st.columns([3, 1, 3])
with col:
    start = st.button('Search', key='lemma_search_btn', use_container_width=True)

if start:
    if not search_lemma:
        st.error('Please select or type a lemma first.')
    else:
        # query_lemmas is a display label "Greek / betacode" — always look up the Greek part
        greek = unicodedata.normalize('NFC', re.sub(r'[)(\\\/=+|]', '', search_lemma.split(' / ')[0].strip()))
        row_indices = lookup.get(greek)

        if row_indices:
            st.session_state['_lemma_page'] = 0
            render_results(kb.iloc[row_indices], page_key='_lemma_page')
        else:
            st.space()
            st.space()
            st.error('No matches')