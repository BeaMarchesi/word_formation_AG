import streamlit as st
import pandas as pd
import base64
from pathlib import Path

RESULTS_PER_PAGE = 30
BRAND_COLOR = '#b32c4b'

def _img_to_base64(path: str) -> str:
    """Convert a local image file to a base64 data URI."""
    data = Path(path).read_bytes()
    ext = Path(path).suffix.lstrip('.')
    mime = 'image/jpeg' if ext.lower() in ('jpg', 'jpeg') else 'image/png'
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def render_sidebar_logos(logos: list[dict]) -> None:
    n = len(logos)
    if n == 0:
        return

    item_width = f"{(100 // n) - 2}%"

    logo_tags = ''
    for logo in logos:
        src = _img_to_base64(logo['path'])
        url = logo.get('url', '#')
        alt = logo.get('alt', '')
        logo_tags += (
            f'<a href="{url}" target="_blank" '
            f'style="display:inline-block; width:{item_width}; margin:0 1%;">'
            f'<img src="{src}" alt="{alt}" '
            f'style="width:100%; height:120; object-fit:contain; border-radius:4px;">'
            f'</a>'
        )

    logo_html = (
        f'<div id="sidebar-logos" style="display:flex; justify-content:center; '
        f'align-items:center; padding:12px 8px 16px 8px; gap:4px;">'
        + logo_tags +
        '</div>'
    )

    # Inject the logos and a small script that moves the div to the top of the sidebar
    st.sidebar.markdown(
        f"""
        {logo_html}
        <script>
            (function() {{
                function moveLogo() {{
                    const logo = window.parent.document.getElementById('sidebar-logos');
                    const sidebar = window.parent.document.querySelector(
                        '[data-testid="stSidebarContent"]'
                    );
                    if (logo && sidebar) {{
                        sidebar.prepend(logo);
                    }} else {{
                        setTimeout(moveLogo, 50);
                    }}
                }}
                moveLogo();
            }})();
        </script>
        """,
        unsafe_allow_html=True,
    )

def render_top_right_logos(logos: list[dict]) -> None:
    n = len(logos)
    if n == 0:
        return

    logo_tags = ''
    for logo in logos:
        src = _img_to_base64(logo['path'])
        url = logo.get('url', '#')
        alt = logo.get('alt', '')
        logo_tags += (
            f'<a href="{url}" target="_blank" '
            f'style="display:inline-block; margin:0 4px;">'
            f'<img src="{src}" alt="{alt}" '
            f'style="height:80px; width:auto; object-fit:contain; border-radius:4px;">'
            f'</a>'
        ) ### modify height to change dimension

    st.markdown(
        f"""
        <div style="
            position: fixed;
            top: 60px;
            right: 20px;
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 8px;
            background: transparent;
        ">
            {logo_tags}
        </div>
        """,
        unsafe_allow_html=True,
    )

def create_export(results: pd.DataFrame) -> bytes:
    def clean_url(url) -> str:
        """Remove parentheses and other characters that break clickable links in CSV."""
        if not isinstance(url, str):
            return ''
        return url.replace('(', '%28').replace(')', '%29')

    export = pd.DataFrame({
        'Lemma': results['lemma'],
        'Meaning': results['meaning'].fillna(''),
        'LSJ Link': results['url'].apply(clean_url),
        'Derivation': results['derivation'].fillna(''),
        'Part of speech': results['part_of_speech'].apply(
            lambda pos: f"{', '.join(pos)}" if isinstance(pos, list) and pos else ''),
        'Prefix': results['prefix'].apply(
            lambda p: f"{'-, '.join(p)}-" if isinstance(p, list) and p else ''),
        'Suffix': results['suffix'].apply(
            lambda s: f"{', '.join(s)}" if isinstance(s, list) and s else ''),
    })
    return export.to_csv(index=False).encode('utf-8')

def render_results(results: pd.DataFrame, page_key: str = '_page') -> None:
    """Render a summary table, then paginated detail cards for each result."""
    total = len(results)
    SUMMARY_THRESHOLD = 2
    total_pages = max(1, -(-total // RESULTS_PER_PAGE))

    # ── Header + badge (always shown) ────────────────────────────────────────
    st.divider()
    st.markdown(
        f"<div style='display:flex; align-items:center; gap:12px; margin-bottom:8px;'>"
        f"<h3 style='color:{BRAND_COLOR}; margin:0;'>Results overview</h3>"
        f"<span style='background-color:{BRAND_COLOR}; color:white; border-radius:12px; "
        f"padding:2px 10px; font-size:0.85rem; font-weight:600; white-space:nowrap;'>"
        f"{total} result{'s' if total != 1 else ''}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Summary table (only when results are numerous enough to warrant it) ──
    if total >= SUMMARY_THRESHOLD:
        st.dataframe(
            results[['lemma', 'meaning', 'part_of_speech', 'derivation']].assign(
                part_of_speech=results['part_of_speech'].apply(
                    lambda x: ', '.join(x) if isinstance(x, list) else x
                )
            ).rename(columns={
                'lemma': 'Lemma',
                'meaning': 'Meaning',
                'part_of_speech': 'Part of speech',
                'derivation': 'Word formation',
            }).fillna(''),
            use_container_width=True,
            hide_index=True,
        )

        _, col, _ = st.columns([2, 1, 2])
        with col:
            st.download_button(
                'Export data',
                data=create_export(results),
                file_name='export_results.csv',
                icon_position='right',
                help='Click to download the results of your query in .csv format',
                on_click='ignore',
                key=1
            )

    st.divider()

    # ── Pagination (only when results exceed one page) ───────────────────────
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    if total_pages > 1:
        first_col, prev_col, info_col, next_col, last_col = st.columns([1, 1, 4, 1, 1])
        current = st.session_state[page_key]

        with first_col:
            if st.button('«', disabled=current == 0, use_container_width=True, help='First page'):
                st.session_state[page_key] = 0
                st.rerun()

        with prev_col:
            if st.button('◀', disabled=current == 0, use_container_width=True, help='Previous page'):
                st.session_state[page_key] -= 1
                st.rerun()

        with info_col:
            st.markdown(
                f"<p style='text-align:center; margin:6px 0;'>"
                f"Page {current + 1} of {total_pages} "
                f"&nbsp;·&nbsp; {RESULTS_PER_PAGE} results per page</p>",
                unsafe_allow_html=True,
            )

        with next_col:
            if st.button('▶', disabled=current >= total_pages - 1, use_container_width=True, help='Next page'):
                st.session_state[page_key] += 1
                st.rerun()

        with last_col:
            if st.button('»', disabled=current >= total_pages - 1, use_container_width=True, help='Last page'):
                st.session_state[page_key] = total_pages - 1
                st.rerun()

        page = st.session_state[page_key]
    else:
        st.session_state[page_key] = 0
        page = 0

    start_idx = page * RESULTS_PER_PAGE
    page_results = results.iloc[start_idx: start_idx + RESULTS_PER_PAGE]

    # ── Detail cards ─────────────────────────────────────────────────────────
    def field_label(text: str) -> str:
        return f"<p style='font-size: 1.1rem; font-weight: 600; margin-bottom: 2px;'>{text}</p>"

    for _, row in page_results.iterrows():
        # Lemma heading
        st.markdown(
            f"<h2 style='text-align: center; color: {BRAND_COLOR};'>{row['lemma']}</h2>",
            unsafe_allow_html=True,
        )

        # ── Meaning — full width ──────────────────────────────────────────────
        st.markdown(field_label('Meaning'), unsafe_allow_html=True)
        if isinstance(row['meaning'], str):
            st.text(row['meaning'])
            st.markdown(
                f'<a href="{row["url"]}" target="_blank" style="color:#1a73e8; text-decoration:underline;">🔗 Go to LSJ entry</a>',
                unsafe_allow_html=True)
        else:
            st.text('Not found')

        # ── Row 1: Derivational base | Part of speech ────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(field_label('Word formation'), unsafe_allow_html=True)
            st.text(row['derivation'] if isinstance(row['derivation'], str) else '—')
        with col2:
            st.markdown(field_label('Part of speech'), unsafe_allow_html=True)
            if isinstance(row['part_of_speech'], list) and row['part_of_speech']:
                st.text(', '.join(row['part_of_speech']))

        # ── Row 2: Prefix | Suffix ───────────────────────────────────────────
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(field_label('Prefix'), unsafe_allow_html=True)
            if isinstance(row['prefix'], list) and row['prefix']:
                st.text(f"{'-, '.join(row['prefix'])}-")
            else:
                st.text('—')
        with col4:
            st.markdown(field_label('Suffix'), unsafe_allow_html=True)
            if isinstance(row['suffix'], list) and row['suffix']:
                st.text(', '.join(row['suffix']))
            else:
                st.text('—')

        st.divider()