import re
import unicodedata

from utils import *
from style import apply_style

apply_style()


CSV_PATH = 'Website/kb.csv'
LOGO_PATH = 'Website/Images/logo_larl_rosso.png'
LOGO_LINK = 'https://linguisticapavia.cdl.unipv.it/it'

POS_OPTIONS = (
    'Any', 'adjective', 'verb', 'noun', 'adverb', 'verb participle',
    'article', 'conjunction', 'preposition', 'pronoun', 'particle',
    'numeral', 'irregular', 'exclamation',
)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    from ast import literal_eval
    return pd.read_csv(
        CSV_PATH,
        converters={
            'etymology_raw': literal_eval,
            'prefix': literal_eval,
            'etymology_betacode': literal_eval,
            'prefix_betacode': literal_eval,
        },
    )


@st.cache_data(show_spinner=False)
def load_compounds() -> list:
    return sorted(
        pd.read_csv('Website/unique_bases.csv')['base'].tolist(),
        key=str.casefold,
    )


def filter_kb(df: pd.DataFrame, lemma: str, pos: str, search_type: str) -> pd.DataFrame:
    """Filter by etymology membership, search type, and POS using vectorised pandas masks."""

    # lemma must appear in etymology_raw list
    mask = df['etymology_raw'].apply(lambda lst: lemma in lst)

    # search_type controls whether we want compounds (>1 base), derivations (==1), or all
    if search_type == 'Composition':
        mask &= df['etymology_raw'].apply(lambda lst: len(lst) > 1)
    elif search_type == 'Derivation':
        mask &= df['etymology_raw'].apply(lambda lst: len(lst) == 1)
    # 'All' → no additional length filter

    if pos != 'Any':
        mask &= df['part_of_speech'] == pos

    return df[mask]

# ── Page layout ───────────────────────────────────────────────────────────────

st.title("Word Formation Ancient Greek", text_alignment='center')
st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)
st.divider()
st.header("Search by lemma and part of speech", text_alignment='center')

kb = load_data()
compounds = load_compounds()

search_lemma = st.selectbox('Search by lemma', options=compounds, key='lemma_pos_select', index=None,
                            help='Both inputs in the Ancient Greek alphabet and in betacode are accepted.\n'
                                 'Inputs in Ancient Greek alphabet must have the correct diacritics. '
                                 '\n Inputs in betacode must be stripped of any diacritics')
search_pos = st.selectbox('Search by part of speech', options=POS_OPTIONS, key='pos_select', index=0)
search_type = st.pills('Search by', options=('Composition', 'Derivation', 'All'), default='All', key='type_pills',
                       help= 'Choose if you want to conduct your query by composition, or derivation. '
                           'The dafault is "All", which shows the results for both options')

_, col, _ = st.columns([3, 1, 3])
with col:
    start = st.button('Search', key='lemma_search_btn', use_container_width=True)

if start:
    if not search_lemma:
        st.error('Please select a lemma')

    else:
        lemma = unicodedata.normalize('NFC', re.sub(r'[)(\\\/=+|*]', '', search_lemma.split(' / ')[0]))
        results = filter_kb(kb, lemma, str(search_pos), search_type).sort_values(
            'lemma', key=lambda s: s.str.casefold()
        )
        if not results.empty:
            st.session_state['_lemma_pos_results'] = results
            st.session_state['_lemma_pos_page'] = 0
        else:
            st.session_state['_lemma_pos_results'] = None

if '_lemma_pos_results' in st.session_state:
    if st.session_state['_lemma_pos_results'] is not None:
        render_results(st.session_state['_lemma_pos_results'],  page_key='_lemma_pos_page')
    else:
        st.space()
        st.space()
        st.error('No matches')

    if st.session_state['_lemma_pos_results'] is not None:
        _, col, _ = st.columns([2, 1, 2])
        with col:
            st.download_button(
                'Export data',
                data=create_export(st.session_state['_lemma_pos_results']),
                file_name='export_results.csv',
                icon_position='right',
                help='Click to download the results of your query in .csv format',
                on_click='ignore',
                key='export_btn',
            )