import streamlit as st
import pandas as pd
from style import apply_style
from utils import BRAND_COLOR

apply_style()

LOGO_PATH = '/Users/beatrice/Desktop/PycharmProjects/Tesi IUSS/Website/Images/logo_larl_rosso.png'
LOGO_LINK = 'https://linguisticapavia.cdl.unipv.it/it'
st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)


# ── Hero ──────────────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div style='text-align: center; padding: 2rem 0 1rem;'>
        <p style='color: grey; font-size: 0.8rem; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 0.5rem;'>
            University of Pavia
        </p>
        <h1 style='color: {BRAND_COLOR}; font-size: 2.4rem; margin: 0.25rem 0;'>
            Word Formation in Ancient Greek
        </h1>
        <p style='color: grey; font-size: 1rem; margin-top: 0.5rem;'>
            A queryable database of derivational morphology
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()


# ── About ─────────────────────────────────────────────────────────────────────

st.markdown(f"<h3 style='color: {BRAND_COLOR};'>About</h3>", unsafe_allow_html=True)
st.markdown("""
This interface provides structured, queryable access to a derivational morphology database
for Ancient Greek, developed at the University of Pavia. The dataset is built on the Brill
dictionary and enriched with affix information, POS tags, and semantic data.

All data and source code are openly available on
[GitHub](https://github.com/BeaMarchesi/word_formation_AG).
The resource is a work in progress; please consult the companion paper for a full
account of its current scope, limitations, and planned extensions.
""")

st.divider()


# ── Data Collection ───────────────────────────────────────────────────────────

st.markdown(f"<h3 style='color: {BRAND_COLOR};'>Data Collection</h3>", unsafe_allow_html=True)
st.markdown(f"""
The database integrates the following layers of information:

**Lemmas and word-formation data** — extracted from the digitised Brill Dictionary, including
prefix information.

**Part-of-speech tags** — sourced from Wiktionary where available (~20k entries, ~15% of
the data); otherwise assigned automatically by the transformer-based parser *odyCy*.

**Suffix data** — sourced from Wiktionary where available (~6.6k entries, ~5% of the data).
For the suffixes *-τηρ* and *-τωρ*, automatic extraction followed by manual validation was applied.
<span style='color: #c0392b;'>⚠ Suffix coverage is still partial</span>, expanding it is a primary goal for future releases.

**Semantic information** — retrieved from the LSJ Lexicon via the Perseus Digital Library,
supplemented by direct links to the corresponding Perseus entries.

For full methodological details and caveats, see the companion paper and GitHub repository.
""", unsafe_allow_html=True)

st.divider()


# ── Resource Structure ────────────────────────────────────────────────────────

st.markdown(f"<h3 style='color: {BRAND_COLOR};'>How to Use</h3>", unsafe_allow_html=True)
st.markdown("""
The database supports two query modes: **by entry** and **by derivation/composition**.

Depending on the mode, searchable parameters include lemma, part of speech, prefix, suffix,
derivation base(s), base POS, and number of bases. Results are displayed both as an overview
table and as individual detailed records, showing all available data for each match. 
Query results can be exported as CSV.
""")

st.divider()


# ── How to Cite ───────────────────────────────────────────────────────────────

st.markdown(f"<h3 style='color: {BRAND_COLOR};'>How to Cite</h3>", unsafe_allow_html=True)
st.markdown("""
If you use this resource, please cite:

> Marchesi, Beatrice. *Ancient Greek Word Formation*. Master's Thesis, IUSS Pavia, 2026.

Please refer to the thesis for a detailed discussion of the resource's design, coverage,
and current limitations.
""")

st.divider()


# ── Contacts ──────────────────────────────────────────────────────────────────

st.markdown(f"<h3 style='color: {BRAND_COLOR};'>Contacts</h3>", unsafe_allow_html=True)
st.markdown("""
For enquiries or to report issues, please contact:

- **Dr Chiara Zanchi** — [chiara.zanchi@unipv.it](mailto:chiara.zanchi@unipv.it)
- **Dr Virginia Mastellari** — [virginia.mastellari@unipv.it](mailto:virginia.mastellari@unipv.it)
""")

st.divider()


# ── Contribute ────────────────────────────────────────────────────────────────

st.markdown(f"<h3 style='color: {BRAND_COLOR};'>Contribute</h3>", unsafe_allow_html=True)
st.markdown("""
We welcome contributions of new data. If you would like to share annotations or corrections,
please download the CSV template below, structure your data accordingly, and contact
Dr Zanchi or Dr Mastellari. Contributors who share data will be acknowledged in the Team section.
""")

df = pd.read_csv('Website/template.csv', sep =';')

st.download_button(
    'Download template',
    data=df.to_csv(index=False),
    file_name='WFAG_template.csv',
    mime='text/csv',
    icon_position='right',
    help='Click to download the csv template of the database structure',
    on_click='ignore',
    key=1
)
