import re
import unicodedata

from utils import *
from style import apply_style

apply_style()

CSV_PATH    = 'Website/kb.csv'
LOGO_PATH   = 'Website/Images/logo_larl_rosso.png'
LOGO_LINK   = 'https://www.facebook.com/groups/251278298330026/?locale=it_IT'

POS_OPTIONS = (
    'Any', 'adjective', 'verb', 'noun', 'adverb', 'verb participle',
    'article', 'conjunction', 'preposition', 'pronoun', 'particle',
    'numeral', 'irregular', 'exclamation',
)

MIN_BASES = 2
MAX_BASES = 6  # Maximum derivation_raw length in the database


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    from ast import literal_eval

    df = pd.read_csv(
        CSV_PATH,
        converters={
            'derivation_raw':      literal_eval,
            'prefix':              literal_eval,
            'derivation_betacode': literal_eval,
            'prefix_betacode':     literal_eval,
        },
    )

    def get_last(lst):
        return lst[-1] if isinstance(lst, list) and lst else None

    df['derivation_last'] = df['derivation_raw'].apply(get_last)
    df['derivation_join'] = df['derivation_raw'].apply(
        lambda x: '|'.join(x) if isinstance(x, list) else ''
    )
    return df


@st.cache_data(show_spinner=False)
def load_filter_options() -> tuple[list, list]:
    prefixes  = sorted(pd.read_csv('Website/unique_prefixes.csv')['prefix'].tolist())
    compounds = sorted(
        pd.read_csv('Website/unique_bases.csv')['base'].tolist(),
        key=str.casefold,
    )
    return prefixes, compounds


@st.cache_data(show_spinner=False)
def build_pos_lookup(lemma_raw: pd.Series, pos: pd.Series) -> dict[str, str]:
    """Map each lemma_raw value to its POS tag (NFC-normalised, quotes stripped)."""
    def clean(s: str) -> str:
        return unicodedata.normalize(
            'NFC',
            s.replace('\u2018', '').replace('\u2019', '')
             .replace('\u201c', '').replace('\u201d', '').strip()
        )
    lookup = {}
    for lemma, tag in zip(lemma_raw, pos):
        if isinstance(lemma, str) and isinstance(tag, str):
            lookup[clean(lemma)] = tag
    return lookup


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_input(raw: str) -> str:
    """Normalise a user-supplied lemma / base string."""
    return unicodedata.normalize('NFC', re.sub(r'[)(\\\/=+|*]', '', raw.split(' / ')[0]))


def _clean_key(s: str) -> str:
    """Same cleaning applied inside derivation_raw lists for POS lookup."""
    return unicodedata.normalize(
        'NFC',
        s.replace('\u2018', '').replace('\u2019', '')
         .replace('\u201c', '').replace('\u201d', '').strip()
    )


# ── Filtering ─────────────────────────────────────────────────────────────────

def filter_kb(
    df:               pd.DataFrame,
    pos_lookup:       dict,
    # classic single-value filters
    lemma:            str | None,
    source_pos:       str,
    destination_pos:  str,
    prefix:           str,
    search_type:      str,
    # positional multi filters — None entries mean "Any / skip"
    multi_bases:      list[str | None] | None = None,
    multi_pos:        list[str | None] | None = None,
    # length range filter (only applied in multi mode)
    min_bases:        int | None = None,
    max_bases:        int | None = None,
) -> pd.DataFrame:
    """Apply all active filters using vectorised pandas masks."""

    mask = pd.Series(True, index=df.index)

    # Always drop rows with empty derivation_raw
    mask &= df['derivation_raw'].apply(
        lambda lst: isinstance(lst, list) and len(lst) > 0
    )

    # ── search type ───────────────────────────────────────────────────────────
    if search_type == 'Composition':
        mask &= df['derivation_raw'].str.len() > 1
    elif search_type == 'Derivation':
        mask &= df['derivation_raw'].str.len() == 1

    # ── destination (lemma) POS ───────────────────────────────────────────────
    if destination_pos != 'Any':
        mask &= df['part_of_speech'] == destination_pos

    # ── prefix ────────────────────────────────────────────────────────────────
    if prefix != 'Any':
        mask &= df['prefix_betacode'].apply(lambda lst: prefix in lst)

    # ── single base (classic mode) ────────────────────────────────────────────
    if lemma is not None:
        mask &= df['derivation_join'].str.contains(re.escape(lemma), na=False)

    # ── single source POS (classic mode) — works independently of base ────────
    if source_pos != 'Any':
        mask &= df['derivation_last_pos'] == source_pos

    # ── length range (multi mode only) ───────────────────────────────────────
    # Applied before positional checks so the range is always enforced.
    if min_bases is not None:
        mask &= df['derivation_raw'].apply(
            lambda lst: isinstance(lst, list) and len(lst) >= min_bases
        )
    if max_bases is not None:
        mask &= df['derivation_raw'].apply(
            lambda lst: isinstance(lst, list) and len(lst) <= max_bases
        )

    # ── positional multi-base filter ─────────────────────────────────────────
    # Each specified (non-None) position must match. The length range above
    # already ensures rows have enough entries, but the idx < len(lst) guard
    # is kept for safety.
    if multi_bases:
        for i, base in enumerate(multi_bases):
            if base is not None:
                clean_base = _clean_input(base)
                mask &= df['derivation_raw'].apply(
                    lambda lst, idx=i, b=clean_base: (
                        idx < len(lst) and
                        unicodedata.normalize('NFC', lst[idx]) == b
                    )
                )

    # ── positional multi-POS filter ───────────────────────────────────────────
    if multi_pos:
        for i, pos_val in enumerate(multi_pos):
            if pos_val is not None and pos_val != 'Any':
                mask &= df['derivation_raw'].apply(
                    lambda lst, idx=i, p=pos_val: (
                        idx < len(lst) and
                        pos_lookup.get(_clean_key(lst[idx])) == p
                    )
                )

    return df[mask]


# ── Page layout ───────────────────────────────────────────────────────────────

st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)
st.title("Word Formation Ancient Greek", text_alignment='center')
st.divider()
st.header("Search by derivation or composition", text_alignment='center')

kb         = load_data()
pos_lookup = build_pos_lookup(kb['lemma_raw'], kb['part_of_speech'])
kb['derivation_last_pos'] = kb['derivation_last'].map(pos_lookup)

sorted_prefixes, compounds = load_filter_options()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Base(s)
# ══════════════════════════════════════════════════════════════════════════════

# Toggle + min/max selectors all on one compact row.
tog_col, _, slider_col = st.columns([3, 0.5, 5])

with tog_col:
    multiple_bases = st.toggle(
        'Advanced base search',
        value=False,
        key='multiple_bases',
        help=(
            'Activate to specify bases and/or their POS by position '
            '(e.g. Base 1 = μυρτάς, POS 2 = verb). '
            'Leave any slot on *Any* to skip it. '
            'Use Min / Max to restrict by number of bases in the result.'
        ),
    )

if multiple_bases:
    with slider_col:
        min_bases_val, max_bases_val = st.select_slider('Select a minumum and a maximum number of bases',
                                                        options= range(MIN_BASES, MAX_BASES + 1), value=(2, 6),
                                                        key='min_max_bases', help='Only return words whose decomposition'
                                                                                  ' has at least the number of minimum '
                                                                                  'bases and up to the number of maximum '
                                                                                  'bases')
    n_slots = max_bases_val
else:
    min_bases_val = None
    max_bases_val = None
    n_slots       = None

# ── Base input(s) ─────────────────────────────────────────────────────────────
if multiple_bases:
    multi_base_values: list[str | None] = []
    for row_start in range(0, n_slots, 3):
        row_range = list(range(row_start, min(row_start + 3, n_slots)))
        n_cols = len(row_range)
        if n_cols == 2:
            col_a, _, col_b = st.columns([4, 0.5, 4])
            for col, i in zip([col_a, col_b], row_range):
                with col:
                    val = st.selectbox(
                        f"Base {i + 1}",
                        options=['Any'] + compounds,
                        key=f'multi_base_{i}',
                        index=0,
                    )
                    multi_base_values.append(val if val != 'Any' else None)
        else:
            cols = st.columns(n_cols)
            for col, i in zip(cols, row_range):
                with col:
                    val = st.selectbox(
                        f"Base {i + 1}",
                        options=['Any'] + compounds,
                        key=f'multi_base_{i}',
                        index=0,
                    )
                    multi_base_values.append(val if val != 'Any' else None)
    st.space()

else:
    multi_base_values = None
    search_lemma = st.selectbox(
        'Search by base',
        options=['Any'] + compounds,
        key='conv_lemma_select',
        index=0,
        help=(
            'Both Ancient Greek alphabet and betacode inputs are accepted.\n'
            'Greek inputs must carry correct diacritics.\n'
            'Betacode inputs must be stripped of diacritics.'
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Base POS
# ══════════════════════════════════════════════════════════════════════════════

if multiple_bases:
    multi_pos_values: list[str | None] = []
    for row_start in range(0, n_slots, 3):
        row_range = range(row_start, min(row_start + 3, n_slots))
        n_cols = len(list(row_range))
        if n_cols == 2:
            col_a, _, col_b = st.columns([4, 0.5, 4])
            for col, i in zip([col_a, col_b], row_range):
                with col:
                    val = st.selectbox(
                        f"Base {i + 1} POS",
                        options=list(POS_OPTIONS),
                        key=f'multi_pos_{i}',
                        index=0,
                    )
                    multi_pos_values.append(val if val != 'Any' else None)

        else:
            cols = st.columns(n_cols)
            for col, i in zip(cols, row_range):
                with col:
                    val = st.selectbox(
                        f"Base {i + 1} POS",
                        options=list(POS_OPTIONS),
                        key=f'multi_pos_{i}',
                        index=0,
                    )
                    multi_pos_values.append(val if val != 'Any' else None)
    st.space()

else:
    multi_pos_values = None
    search_source_pos = st.selectbox(
        'Search by base part of speech',
        options=POS_OPTIONS,
        key='conv_source_pos_select',
        index=0,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Lemma POS · Prefix · Search type
# ══════════════════════════════════════════════════════════════════════════════

col1, _, col2 = st.columns([4, 0.5, 4])
with col1:
    search_destination_pos = st.selectbox(
        'Search by lemma part of speech',
        options=POS_OPTIONS,
        key='conv_dest_pos_select',
        index=0,
    )
with col2:
    search_prefix = st.selectbox(
        'Search by prefix',
        options=sorted_prefixes,
        index=0,
        key='conv_prefix_select',
        help=(
            'Both Ancient Greek alphabet and betacode inputs are accepted.\n'
            'Both types must be stripped of diacritics.'
        ),
    )

prefix_val = (
    str(search_prefix).split(' / ')[1]
    if ' / ' in str(search_prefix)
    else str(search_prefix)
)

if prefix_val != 'Any' or multiple_bases:
    search_type = st.pills(
        'Search by',
        options=('Composition',),
        default='Composition',
        key='conv_type_pills',
        help='A specific prefix or multiple-bases query implies composition.',
    )
else:
    search_type = st.pills(
        'Search by',
        options=('Composition', 'Derivation', 'All'),
        default='All',
        key='conv_type_pills',
        help='Choose composition, derivation, or both.',
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Search button
# ══════════════════════════════════════════════════════════════════════════════

_, btn_col, _ = st.columns([3, 1, 3])
with btn_col:
    start = st.button('Search', key='conv_search_btn', use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Execute search
# ══════════════════════════════════════════════════════════════════════════════

if start:
    dest_pos_val = str(search_destination_pos)

    if multiple_bases:
        lemma          = None
        source_pos_val = 'Any'
    else:
        lemma = (
            _clean_input(search_lemma)
            if search_lemma and search_lemma != 'Any'
            else None
        )
        source_pos_val = (
            str(search_source_pos) if search_source_pos is not None else 'Any'
        )

    multi_bases_active = multi_base_values and any(v is not None for v in multi_base_values)
    multi_pos_active   = multi_pos_values   and any(v is not None for v in multi_pos_values)
    # In multi mode, even if all slots are Any, the min/max range itself counts
    # as an active filter (user explicitly chose to restrict by length).
    range_active = multiple_bases  # min/max are always set when toggle is on

    no_filters = (
        lemma is None
        and dest_pos_val   == 'Any'
        and prefix_val     == 'Any'
        and source_pos_val == 'Any'
        and not multi_bases_active
        and not multi_pos_active
        and not range_active
    )

    if no_filters:
        st.error('Please select at least one filter value.')
    else:
        results = filter_kb(
            kb,
            pos_lookup,
            lemma           = lemma,
            source_pos      = source_pos_val,
            destination_pos = dest_pos_val,
            prefix          = prefix_val,
            search_type     = str(search_type) if search_type else 'All',
            multi_bases     = multi_base_values if multiple_bases else None,
            multi_pos       = multi_pos_values  if multiple_bases else None,
            min_bases       = min_bases_val,
            max_bases       = max_bases_val,
        ).sort_values('lemma', key=lambda s: s.str.casefold())

        st.session_state['_derivation_results'] = results if not results.empty else None
        st.session_state['_derivation_page']    = 0


# ══════════════════════════════════════════════════════════════════════════════
# Render results
# ══════════════════════════════════════════════════════════════════════════════

if '_derivation_results' in st.session_state:
    if st.session_state['_derivation_results'] is not None:
        render_results(st.session_state['_derivation_results'], page_key='_derivation_page')

        _, dl_col, _ = st.columns([2, 1, 2])
        with dl_col:
            st.download_button(
                'Export data',
                data          = create_export(st.session_state['_derivation_results']),
                file_name     = 'export_results.csv',
                icon_position = 'right',
                help          = 'Download the results of your query as a .csv file.',
                on_click      = 'ignore',
                key           = 'conv_export_btn',
            )
    else:
        st.space()
        st.space()
        st.error('No matches found.')