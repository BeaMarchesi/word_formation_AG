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
def load_filter_options() -> tuple[list, list]:
    suffixes = pd.read_csv('Website/unique_suffixes.csv')['suffixes'].tolist()
    prefixes = pd.read_csv('Website/unique_prefixes.csv')['prefix'].tolist()
    return sorted(suffixes), sorted(prefixes)


def filter_kb(df: pd.DataFrame, pos: str, prefix: str, suffix: str) -> pd.DataFrame:
    """Apply the active filters using pandas boolean masks — no Python loops."""
    mask = pd.Series(True, index=df.index)

    if pos != 'Any':
        mask &= df['part_of_speech'] == pos

    if prefix != 'Any':
        # prefix column holds lists; check membership vectorised
        mask &= df['prefix_betacode'].apply(lambda lst: prefix in lst)

    if suffix != 'Any':
        mask &= df['suffix'] == suffix

    return df[mask]

# ── Page layout ───────────────────────────────────────────────────────────────

st.title("Word Formation Ancient Greek", text_alignment='center')
st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)
st.divider()
st.header("Search by part of speech and affix", text_alignment='center')

kb = load_data()
sorted_suffixes, sorted_prefixes = load_filter_options()

search_pos = st.selectbox('Search by part of speech', options=POS_OPTIONS, key='pos_select', index=0)

col1, _, col2 = st.columns([4, 0.5, 4])

with col1:
    search_prefix = st.selectbox('Search by prefix', options=sorted_prefixes, key='prefix_select', index=0,
                             help= 'Both inputs in the Ancient Greek alphabet and in betacode are accepted. \n'
                                  'Both types of input must be stripped of diacritics')

with col2:
    search_suffix = st.selectbox('Search by suffix', options=sorted_suffixes, key='suffix_select', index=0,
                             help='Both inputs in the Ancient Greek alphabet and in betacode are accepted. \n'
                                  'Both types of input must be stripped of diacritics')

_, col, _ = st.columns([3, 1, 3])
with col:
    start = st.button('Search', key='lemma_search_btn', use_container_width=True)

if start:
    prefix_val = str(search_prefix).split(' / ')[1] if ' / ' in str(search_prefix) else str(search_prefix)
    suffix_val = str(search_suffix).split(' / ')[1] if ' / ' in str(search_suffix) else str(search_suffix)
    pos_val = str(search_pos)
    if pos_val == 'Any' and prefix_val == 'Any' and suffix_val == 'Any':
        st.error('Please select at least a value')
    else:
        results = filter_kb(kb, pos_val, prefix_val, suffix_val).sort_values('lemma', key=lambda s: s.str.casefold())

        if not results.empty:
            st.session_state['_pos_affix_results'] = results
            st.session_state['_pos_affix_page'] = 0
        else:
            st.session_state['_pos_affix_results'] = None

if '_pos_affix_results' in st.session_state:
    if st.session_state['_pos_affix_results'] is not None:
        render_results(st.session_state['_pos_affix_results'], page_key='_pos_affix_page')
    else:
        st.space()
        st.space()
        st.error('No matches')

    if st.session_state['_pos_affix_results'] is not None:
        _, col, _ = st.columns([2, 1, 2])
        with col:
            st.download_button(
                'Export data',
                data=create_export(st.session_state['_pos_affix_results']),
                file_name='export_results.csv',
                icon_position='right',
                help='Click to download the results of your query in .csv format',
                on_click='ignore',
                key='export_btn',
            )