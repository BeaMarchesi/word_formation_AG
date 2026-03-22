import unicodedata
import re

import streamlit as st
import pandas as pd

from utils import *
from style import apply_style

apply_style()

CSV_PATH = 'Website/kb.csv'
LOGO_PATH = 'Website/Images/logo_larl_rosso.png'
LOGO_LINK = 'https://www.facebook.com/groups/251278298330026/?locale=it_IT'

POS_OPTIONS = (
    'Any', 'adjective', 'verb', 'noun', 'adverb', 'verb participle',
    'article', 'conjunction', 'preposition', 'pronoun', 'particle',
    'numeral', 'irregular', 'exclamation',
)

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    from ast import literal_eval
    return pd.read_csv(CSV_PATH, converters={'derivation_raw': literal_eval, 'prefix': literal_eval})


@st.cache_data(show_spinner=False)
def build_lookup(lemma_raw: pd.Series, betacode_raw: pd.Series) -> dict:
    """Build lookup dict by passing only Series (not full DataFrame) to avoid
    cache hashing errors caused by list-typed columns like prefix/derivation_raw."""
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
def load_filter_options() -> tuple[list, list]:
    suffixes = pd.read_csv('Website/unique_suffixes.csv')['suffixes'].tolist()
    prefixes = pd.read_csv('Website/unique_prefixes.csv')['prefix'].tolist()
    return sorted(suffixes), sorted(prefixes)


@st.cache_data(show_spinner=False)
def build_options(query_lemmas: pd.Series) -> list[str]:
    """Return sorted display labels, safely dropping NaN floats."""
    return sorted(
        [v for v in query_lemmas if isinstance(v, str)],
        key=str.casefold,
    )

def filter_kb(df: pd.DataFrame, lemma: str, pos: str, prefix: str) -> pd.DataFrame:
    """Apply the active filters using pandas boolean masks — no Python loops."""
    mask = pd.Series(True, index=df.index)

    if lemma:
        mask &= df['lemma_raw'] == lemma

    if pos != 'Any':
        mask &= df['part_of_speech'] == pos

    if prefix != 'Any':
        # prefix column holds lists; check membership vectorised
        mask &= df['prefix_betacode'].apply(lambda lst: prefix in lst)

    return df[mask]


# ── Page layout ───────────────────────────────────────────────────────────────

st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)
st.title("Word Formation Ancient Greek", text_alignment = 'center')
st.divider()
st.header("Search by entry", text_alignment = 'center')

kb = load_data()
lookup = build_lookup(kb['lemma_raw'], kb['lemma_betacode_raw'])
options = build_options(kb['query_lemmas'])

search_lemma = st.selectbox(
    'Search by lemma',
    options=options,
    key='lemma_selectbox',
    index=None,
    accept_new_options=True,
    help='Both inputs in the Ancient Greek alphabet and in betacode are accepted.\n'
         'Inputs in the Ancient Greek alphabet must have the correct diacritics.\n'
         'Inputs in betacode must be stripped of any diacritics.',
)
sorted_suffixes, sorted_prefixes = load_filter_options()

col1, _, col2 = st.columns([4, 0.5, 4])

with col1:
    search_pos = st.selectbox('Search by part of speech', options=POS_OPTIONS, key='pos_select', index=0)

with col2:
    search_prefix = st.selectbox('Search by prefix', options=sorted_prefixes, key='prefix_select', index=0,
                             help= 'Both inputs in the Ancient Greek alphabet and in betacode are accepted. \n'
                                  'Both types of input must be stripped of diacritics')

_, col, _ = st.columns([3, 1, 3])
with col:
    start = st.button('Search', key='lemma_search_btn', use_container_width=True)

if start:
    prefix_val = str(search_prefix).split(' / ')[1] if ' / ' in str(search_prefix) else str(search_prefix)
    pos_val = str(search_pos)
    if not search_lemma and pos_val == 'Any' and prefix_val == 'Any' :
        st.error('Please select at least a value')
    else:
        if search_lemma:
            search_lemma = unicodedata.normalize('NFC', re.sub(r'[)(\\\/=+|]', '', search_lemma.split(' / ')[0].strip()))
        results = filter_kb(kb, search_lemma, pos_val, prefix_val).sort_values('lemma', key=lambda s: s.str.casefold())

        if not results.empty:
            st.session_state['_entry_results'] = results
            st.session_state['_entry_page'] = 0
        else:
            st.session_state['_entry_results'] = None

if '_entry_results' in st.session_state:
    if st.session_state['_entry_results'] is not None:
        render_results(st.session_state['_entry_results'], page_key='_entry_page')
    else:
        st.space()
        st.space()
        st.error('No matches')

    if st.session_state['_entry_results'] is not None:
        _, col, _ = st.columns([2, 1, 2])
        with col:
            st.download_button(
                'Export data',
                data=create_export(st.session_state['_entry_results']),
                file_name='export_results.csv',
                icon_position='right',
                help='Click to download the results of your query in .csv format',
                on_click='ignore',
                key='export_btn',
            )