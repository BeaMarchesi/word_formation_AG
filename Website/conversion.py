import re
import unicodedata

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

    df = pd.read_csv(
        CSV_PATH,
        converters={
            'etymology_raw': literal_eval,
            'prefix': literal_eval,
            'etymology_betacode': literal_eval,
            'prefix_betacode': literal_eval,
        },
    )

    def get_last(lst):
        if isinstance(lst, list) and len(lst) > 0:
            return lst[-1]
        return None

    df['etymology_last'] = df['etymology_raw'].apply(get_last)

    df['etymology_join'] = df['etymology_raw'].apply(
        lambda x: '|'.join(x) if isinstance(x, list) else ''
    )

    return df

@st.cache_data(show_spinner=False)
def load_filter_options() -> tuple[list, list, list]:
    prefixes = sorted(pd.read_csv('Website/unique_prefixes.csv')['prefix'].tolist())
    suffixes = sorted(pd.read_csv('Website/unique_suffixes.csv')['suffixes'].tolist())
    compounds = sorted(
        pd.read_csv('Website/unique_bases.csv')['base'].tolist(),
        key=str.casefold,
    )
    return prefixes, suffixes, compounds


@st.cache_data(show_spinner=False)
def build_pos_lookup(lemma_raw: pd.Series, pos: pd.Series) -> dict[str, str]:
    """Map each lemma_raw to its POS tag.
    Smart/curly quotes are stripped and NFC normalisation applied so keys match
    the cleaned etymology_raw entries used in the filter."""
    def clean(s: str) -> str:
        return unicodedata.normalize('NFC', s.replace('‘', '').replace('’', '').replace('“', '').replace('”', '').strip())

    lookup = {}
    for lemma, tag in zip(lemma_raw, pos):
        if not isinstance(tag, str):
            continue
        if isinstance(lemma, str):
            lookup[clean(lemma)] = tag
    return lookup



def filter_kb(df: pd.DataFrame, pos_lookup: dict, lemma: str | None, source_pos: str,
              destination_pos: str, prefix: str, suffix: str,
              search_type: str) -> pd.DataFrame:
    """Apply all active filters using vectorised pandas masks."""

    mask = pd.Series(True, index=df.index)

    # Always filter out entries with empty etymology_raw
    mask &= df['etymology_raw'].apply(lambda lst: isinstance(lst, list) and len(lst) > 0)

    if lemma is not None:
        mask &= df['etymology_join'].str.contains(re.escape(lemma), na=False)

    if search_type == 'Composition':
        mask &= df['etymology_raw'].str.len() > 1
    elif search_type == 'Derivation':
        mask &= df['etymology_raw'].str.len() == 1

    if source_pos != 'Any':
        mask &= df['etymology_last_pos'] == source_pos

    if destination_pos != 'Any':
        mask &= df['part_of_speech'] == destination_pos

    if prefix != 'Any':
        mask &= df['prefix_betacode'].apply(lambda lst: prefix in lst)

    if suffix != 'Any':
        mask &= df['suffix'] == suffix

    return df[mask]
# ── Page layout ───────────────────────────────────────────────────────────────

st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)
st.title("Word Formation Ancient Greek", text_alignment = 'center')
st.divider()
st.header("Search by conversion", text_alignment = 'center')

kb = load_data()
pos_lookup = build_pos_lookup(kb['lemma_raw'], kb['part_of_speech'])
kb['etymology_last_pos'] = kb['etymology_last'].map(pos_lookup)

sorted_prefixes, sorted_suffixes, compounds = load_filter_options()

search_lemma = st.selectbox(
    'Search by lemma', options=['Any'] + compounds, key='conv_lemma_select', index=0,
    help='Both inputs in the Ancient Greek alphabet and in betacode are accepted.\n'
         'Inputs in the Ancient Greek alphabet must have the correct diacritics.\n'
         'Inputs in betacode must be stripped of any diacritics.',
)

col1, _, col2 = st.columns([4, 0.5, 4])

with col1:
    search_source_pos = st.selectbox(
        'Search by source part of speech',
        options=[o for o in POS_OPTIONS if o != 'Any'],  # mandatory
        key='conv_source_pos_select', index=None,
    )

with col2:
    search_destination_pos = st.selectbox(
        'Search by destination part of speech', options=POS_OPTIONS,
        key='conv_dest_pos_select', index=0,
    )

with col1:
    search_prefix = st.selectbox(
        'Search by prefix', options=sorted_prefixes, index=0,
        key='conv_prefix_select',
        help='Both inputs in the Ancient Greek alphabet and in betacode are accepted.\n'
             'Both types of input must be stripped of diacritics.',
    )

with col2:
    search_suffix = st.selectbox(
        'Search by suffix', options=sorted_suffixes, index=0,
        key='conv_suffix_select',
        help='Both inputs in the Ancient Greek alphabet and in betacode are accepted.\n'
             'Both types of input must be stripped of diacritics.',
    )

prefix_val = str(search_prefix).split(' / ')[1] if ' / ' in str(search_prefix) else str(search_prefix)
if prefix_val != 'Any':
    search_type = st.pills(
        'Search by', options=('Composition',), default='Composition',
        key='conv_type_pills',
        help='A specific prefix implies composition.',
    )
else:
    search_type = st.pills(
        'Search by', options=('Composition', 'Derivation', 'All'), default='All',
        key='conv_type_pills',
        help='Choose composition, derivation, or both.',
    )

_, col, _ = st.columns([3, 1, 3])
with col:
    start = st.button('Search', key='conv_search_btn', use_container_width=True)

if start:
    if search_source_pos is None:
        st.error('Please select at least a source part-of-speech')
    else:
        suffix_val = str(search_suffix).split(' / ')[1] if ' / ' in str(search_suffix) else str(search_suffix)
        source_pos_val = str(search_source_pos) if search_source_pos is not None else 'Any'
        dest_pos_val = str(search_destination_pos)

        no_filters = (
            search_lemma == 'Any'
            and dest_pos_val == 'Any'
            and prefix_val == 'Any'
            and suffix_val == 'Any'
            and source_pos_val == 'Any'
        )

        if no_filters:
            st.error('Please select at least a source part-of-speech')
        else:
            lemma = None
            if search_lemma and search_lemma != "Any":
                lemma = unicodedata.normalize('NFC', re.sub(r'[)(\\\/=+|*]', '', search_lemma.split(' / ')[0]))

            results = filter_kb(kb, pos_lookup, lemma, source_pos_val, dest_pos_val, prefix_val, suffix_val, search_type).sort_values(
                'lemma', key=lambda s: s.str.casefold()
            )

            if not results.empty:
                st.session_state['_conversion_results'] = results
                st.session_state['_conversion_page'] = 0
            else:
                st.session_state['_conversion_results'] = None

if '_conversion_results' in st.session_state:
    if st.session_state['_conversion_results'] is not None:
        render_results(st.session_state['_conversion_results'], page_key='_conversion_page')
    else:
        st.space()
        st.space()
        st.error('No matches')

    if st.session_state['_conversion_results'] is not None:
        _, col, _ = st.columns([2, 1, 2])
        with col:
            st.download_button(
                'Export data',
                data=create_export(st.session_state['_conversion_results']),
                file_name='export_results.csv',
                icon_position='right',
                help='Click to download the results of your query in .csv format',
                on_click='ignore',
                key='conv_export_btn',
            )