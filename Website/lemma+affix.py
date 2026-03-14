import re
import unicodedata

from utils import *
from style import apply_style

apply_style()

CSV_PATH = 'Website/kb.csv'
LOGO_PATH = 'Website/Images/logo_larl_rosso.png'
LOGO_LINK = 'https://linguisticapavia.cdl.unipv.it/it'


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
def load_filter_options() -> tuple[list, list, list]:
    prefixes = sorted(
        pd.read_csv('/Website/unique_prefixes.csv')['prefix'].tolist()
    )
    suffixes = sorted(
        pd.read_csv('Website/unique_suffixes.csv')['suffixes'].tolist()
    )
    compounds = sorted(
        pd.read_csv('Website/unique_bases.csv')['base'].tolist(),
        key=str.casefold,
    )
    return prefixes, suffixes, compounds


def filter_kb(df: pd.DataFrame, lemma: str, prefix: str, suffix: str, search_type: str) -> pd.DataFrame:
    """Apply all active filters using vectorised pandas masks — no Python loops."""

    # lemma must appear in etymology_raw list
    mask = df['etymology_raw'].apply(lambda lst: lemma in lst)

    # search_type constrains the length of the etymology list
    if search_type == 'Composition':
        mask &= df['etymology_raw'].apply(lambda lst: len(lst) > 1)
    elif search_type == 'Derivation':
        mask &= df['etymology_raw'].apply(lambda lst: len(lst) == 1)
    # 'All' → no length constraint

    if prefix != 'Any':
        mask &= df['prefix_betacode'].apply(lambda lst: prefix in lst)

    if suffix != 'Any':
        mask &= df['suffix'] == suffix

    return df[mask]


# ── Page layout ───────────────────────────────────────────────────────────────

st.title("Word Formation Ancient Greek", text_alignment='center')
st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)
st.divider()
st.header("Search by lemma and affix", text_alignment='center')

kb = load_data()
sorted_prefixes, sorted_suffixes, compounds = load_filter_options()

search_lemma = st.selectbox('Search by lemma', options=compounds, key='lemma_affix_select',
                            index=None, help='Both inputs in the Ancient Greek alphabet and in betacode are accepted.\n'
                                             'Inputs in Ancient Greek alphabet must have the correct diacritics. '
                                             '\n Inputs in betacode must be stripped of any diacritics')

# Disable affix selectors until a lemma is chosen
disabled = search_lemma is None

col1, _, col2 = st.columns([4, 0.5, 4])
with col1:
    search_prefix = st.selectbox('Search by prefix', options=sorted_prefixes, index=0,
                                 key='prefix_select', disabled=disabled,
                                 help='Both inputs in the Ancient Greek alphabet and in betacode are accepted. \n'
                                      'Both types of input must be stripped of diacritics')
with col2:
    search_suffix = st.selectbox('Search by suffix', options=sorted_suffixes, index=0,
                                 key='suffix_select', disabled=disabled,
                                 help='Both inputs in the Ancient Greek alphabet and in betacode are accepted. \n'
                                      'Both types of input must be stripped of diacritics')

# When a prefix is active, only Composition makes sense
prefix_val = str(search_prefix).split(' / ')[1] if ' / ' in str(search_prefix) else str(search_prefix)
if prefix_val != 'Any':
    search_type = st.pills('Search by', options=('Composition',), default='Composition', key='type_pills',
                           help='A specific prefix implies composition')
else:
    search_type = st.pills('Search by', options=('Composition', 'Derivation', 'All'), default='All', key='type_pills',
                           help='Choose if you want to conduct your query by composition, or derivation. '
                           'The dafault is "All", which shows the results for both options')

_, col, _ = st.columns([3, 1, 3])
with col:
    start = st.button('Search', key='lemma_search_btn', use_container_width=True)

if start:
    if not search_lemma:
        st.error('Please select a lemma')
    else:
        lemma = unicodedata.normalize('NFC', re.sub(r'[)(\\\/=+|*]', '', search_lemma.split(' / ')[0]))
        suffix_val = str(search_suffix).split(' / ')[1] if ' / ' in str(search_suffix) else str(search_suffix)

        results = filter_kb(kb, lemma, prefix_val, suffix_val, search_type).sort_values(
            'lemma', key=lambda s: s.str.casefold()
        )
        if not results.empty:
            st.session_state['_lemma_affix_results'] = results
            st.session_state['_lemma_affix_page'] = 0
        else:
            st.session_state['_lemma_affixs_results'] = None

if '_lemma_affix_results' in st.session_state:
    if st.session_state['_lemma_affix_results'] is not None:
        render_results(st.session_state['_lemma_affix_results'])
    else:
        st.space()
        st.space()
        st.error('No matches')

    if st.session_state['_lemma_affix_results'] is not None:
        _, col, _ = st.columns([2, 1, 2])
        with col:
            st.download_button(
                'Export data',
                data=create_export(st.session_state['_lemma_affix_results']),
                file_name='export_results.csv',
                icon_position='right',
                help='Click to download the results of your query in .csv format',
                on_click='ignore',
                key='export_btn',
            )