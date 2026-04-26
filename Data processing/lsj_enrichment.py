import asyncio
import random
import re
import time
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET

import aiohttp
import pandas as pd

# -- Unicode -> Beta Code -----------------------------------------------------
# NOTE: Only used internally by _resolve_lemmas to convert Unicode lemma forms
# returned by Morpheus back to Beta Code for LSJ lookup.
# The input DataFrame columns are expected to already contain Beta Code.

_COMBINING_TO_BETA: dict[str, str] = {
    "\u0313": ")",  # smooth breathing
    "\u0314": "(",  # rough breathing
    "\u0301": "/",  # acute
    "\u0300": "\\", # grave
    "\u0342": "=",  # circumflex
    "\u0308": "+",  # diaeresis
    "\u0345": "|",  # iota subscript
}
_GREEK_BASE_TO_BETA: dict[str, str] = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e",
    "ζ": "z", "η": "h", "θ": "q", "ι": "i", "κ": "k",
    "λ": "l", "μ": "m", "ν": "n", "ξ": "c", "ο": "o",
    "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
    "υ": "u", "φ": "f", "χ": "x", "ψ": "y", "ω": "w",
}
_DIACRITIC_ORDER: list[str] = [
    "\u0313", "\u0314", "\u0301", "\u0300", "\u0342", "\u0308", "\u0345",
]


def greek_unicode_to_betacode(text: str) -> str:
    """Convert a Greek Unicode string to TLG-style Beta Code."""
    nfd = unicodedata.normalize("NFD", text)
    result: list[str] = []
    i = 0
    while i < len(nfd):
        ch = nfd[i]
        j = i + 1
        combining: list[str] = []
        while j < len(nfd) and unicodedata.category(nfd[j]).startswith("M"):
            combining.append(nfd[j])
            j += 1

        lower_ch = ch.lower()
        if lower_ch in _GREEK_BASE_TO_BETA:
            beta_base = _GREEK_BASE_TO_BETA[lower_ch]
            is_upper = unicodedata.category(ch) == "Lu"
            diacritics = "".join(
                _COMBINING_TO_BETA[c]
                for c in _DIACRITIC_ORDER
                if c in combining
            )
            if is_upper:
                result.append("*" + diacritics + beta_base.upper())
            else:
                result.append(beta_base + diacritics)
        elif ch == "·":
            result.append(":")
        elif ch == ";":
            result.append("?")
        elif not unicodedata.category(ch).startswith("M"):
            result.append(ch)
        i = j

    return "".join(result)


# -- Perseus URLs -------------------------------------------------------------

_XML_BASE    = "https://www.perseus.tufts.edu/hopper/xmlchunk?doc=Perseus:text:1999.04.0057:entry="
_BROWSE_BASE = "https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057:entry="
_HEADERS     = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0 Safari/537.36"
    )
}

_MORPH_BASE = "https://www.perseus.tufts.edu/hopper/xmlmorph?lang=greek&lookup="

_RATE_LIMIT_STATUSES = frozenset({429, 503})


# -- Token-bucket rate limiter ------------------------------------------------

class _RateLimiter:
    """
    Token-bucket rate limiter shared across all coroutines.

    Allows at most `rate` requests per second on average.  The bucket starts
    full so the very first requests go out immediately without any forced delay.
    An asyncio.Lock ensures there is no double-spending between concurrent tasks.
    """

    def __init__(self, rate: float) -> None:
        self._rate   = rate
        self._tokens = rate          # start full
        self._last   = time.monotonic()
        self._lock   = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now     = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
            self._last   = now
            if self._tokens < 1:
                wait = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1


# -- Sense extraction ---------------------------------------------------------

# Match single uppercase letters (A, B, C …) or Roman numerals (I, II, IV …)
# as top-level sense markers.
_TOP_LEVEL_SENSE_RE = re.compile(r"^(?:[IVX]+|[A-Z])$")

def _find_all(root, tag):
    return [e for e in root.iter() if e.tag == tag or e.tag.endswith("}" + tag)]


def _bare_tag(elem) -> str:
    t = elem.tag
    return t.split("}")[-1] if "}" in t else t


def _collect_tr_outside_cit(sense_elem) -> list[str]:
    """
    Collect <tr> text within a <sense>, excluding:
    - any <tr> inside a <cit> block
    - any <tr> that is the immediate sibling following a <foreign> element
      (i.e. translation of an inline Greek expression, not a standalone gloss)
    """
    results = []

    def _walk(node, inside_cit=False):
        tag = _bare_tag(node)

        if tag == "cit":
            for child in node:
                _walk(child, inside_cit=True)
            return

        if tag == "tr":
            if not inside_cit:
                text = (node.text or "").strip().strip(",;:. —–")
                if text:
                    results.append(text)
            return

        # Track siblings to detect <tr> preceded by <foreign>
        children = list(node)
        prev_tag = None
        for child in children:
            ctag = _bare_tag(child)
            if ctag == "tr" and prev_tag == "foreign":
                # Skip: this <tr> translates the preceding <foreign> expression
                prev_tag = ctag
                continue
            _walk(child, inside_cit=inside_cit)
            prev_tag = ctag

    # Start walking children of sense (not sense itself)
    children = list(sense_elem)
    prev_tag = None
    for child in children:
        ctag = _bare_tag(child)
        if ctag == "tr" and prev_tag == "foreign":
            prev_tag = ctag
            continue
        _walk(child, inside_cit=False)
        prev_tag = ctag

    return results


def _sense_text(sense_elem) -> str:
    """
    Build a clean definition string from a <sense> by joining all valid
    <tr> fragments that are not inside <cit> blocks.
    """
    parts = _collect_tr_outside_cit(sense_elem)
    if not parts:
        return ""

    # Deduplicate preserving order
    seen = set()
    deduped = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            deduped.append(p)

    # Join with "; " — fragments within one sense belong together
    text = "; ".join(deduped)

    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip(".,;: —–")
    return text.strip()


def extract_top_level_senses(root) -> list[str]:
    all_senses = _find_all(root, "sense")
    top = [s for s in all_senses if _TOP_LEVEL_SENSE_RE.match(s.get("n", ""))]
    if not top:
        top = [s for s in all_senses if s.get("level") == "1"]
    if not top:
        top = all_senses
    return [g for g in (_sense_text(s) for s in top) if g]


def format_meanings(senses: list[str]) -> str:
    return "\n".join(f"- {s}" for s in senses) if senses else ""


# -- Async fetch helpers ------------------------------------------------------

def _jitter(base_delay: float, attempt: int) -> float:
    """Full-jitter exponential back-off: uniform in [0, base * 2^attempt]."""
    return random.uniform(0, base_delay * (2 ** attempt))


async def _fetch_xml(
    session:      aiohttp.ClientSession,
    rate_limiter: _RateLimiter,
    bc:           str,
    max_retries:  int,
    base_delay:   float,
    label:        str,
) -> bytes | None:
    """
    Fetch LSJ XML for *bc* with retry logic:

    - Token-bucket rate limiting throttles throughput before every attempt.
    - 429 / 503 responses trigger an extended pause (honouring Retry-After
      when present) and then loop back — they do NOT count as failed attempts.
    - All other errors use full-jitter exponential backoff and count toward
      max_retries.
    """
    url     = _XML_BASE + bc
    attempt = 0

    while attempt < max_retries:
        await rate_limiter.acquire()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:

                if resp.status in _RATE_LIMIT_STATUSES:
                    retry_after = resp.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        pause = float(retry_after)
                    else:
                        # Escalating pause: 60 s, 120 s, 240 s, 480 s, then capped
                        pause = min(60.0 * (2 ** min(attempt, 3)), 480.0)
                    print(
                        f"    {label} -> HTTP {resp.status} (rate-limited), "
                        f"pausing {pause:.0f}s …"
                    )
                    await asyncio.sleep(pause)
                    continue  # retry without consuming an attempt

                resp.raise_for_status()
                return await resp.read()

        except aiohttp.ClientResponseError as e:
            if attempt == max_retries - 1:
                print(f"    {label} -> [HTTP {e.status} after {max_retries} attempts]")
                return None
            wait = _jitter(base_delay, attempt)
            print(f"    {label} -> [HTTP {e.status}, attempt {attempt+1}] retrying in {wait:.1f}s")
            await asyncio.sleep(wait)

        except Exception as e:
            if attempt == max_retries - 1:
                print(f"    {label} -> [failed after {max_retries} attempts: {e}]")
                return None
            wait = _jitter(base_delay, attempt)
            print(f"    {label} -> [attempt {attempt+1} error: {e}] retrying in {wait:.1f}s")
            await asyncio.sleep(wait)

        attempt += 1

    return None


async def _resolve_lemmas(
    session:      aiohttp.ClientSession,
    rate_limiter: _RateLimiter,
    bc_stripped:  str,
) -> list[str]:
    """
    Query Perseus Morpheus for *bc_stripped* and return deduplicated Beta Code
    headwords.  Rate-limited; returns [] on any failure. A single automatic
    retry is attempted on 429/503.
    """
    url = _MORPH_BASE + bc_stripped

    for attempt in range(2):  # one normal try + one retry after rate-limit pause
        await rate_limiter.acquire()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status in _RATE_LIMIT_STATUSES:
                    pause = 60.0
                    print(f"    [Morpheus] HTTP {resp.status}, pausing {pause:.0f}s …")
                    await asyncio.sleep(pause)
                    continue  # go to attempt 1
                resp.raise_for_status()
                xml_bytes = await resp.read()
                break
        except Exception:
            return []
    else:
        return []  # both attempts failed

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    seen, result = set(), []
    for elem in root.iter("lemma"):
        text = (elem.text or "").strip()
        if text:
            bc_lemma = greek_unicode_to_betacode(text)
            if bc_lemma not in seen:
                seen.add(bc_lemma)
                result.append(bc_lemma)
    return result


def _parse_glosses(xml_bytes: bytes):
    """Parse XML bytes; return (senses, formatted) or None on parse error."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    senses = extract_top_level_senses(root)
    return senses, format_meanings(senses)


# -- Per-lemma orchestration --------------------------------------------------

async def _fetch_one(
    session:        aiohttp.ClientSession,
    semaphore:      asyncio.Semaphore,
    rate_limiter:   _RateLimiter,
    idx:            int,
    total:          int,
    lemma:          str,
    stripped_bc:    str,
    xml_dir:        Path | None,
    max_retries:    int,
    base_delay:     float,
    fallback_log:   list[tuple[str, str]],  # shared list; GIL-safe for list.append
) -> tuple[int, str, str]:
    """
    Fetch and parse the LSJ entry for *lemma*.  Always returns (idx, meaning, url).

    Stage 1 — direct lookup with rate-limited, jittered exponential backoff.
               Raw XML is saved to *xml_dir* on success.
    Stage 2 — if no glosses found, query Morpheus for canonical headword(s)
               and retry the LSJ lookup for each candidate.

    When stage 2 succeeds, (lemma, headword_bc) is appended to *fallback_log*
    so the caller can write the trace file.

    The URL is populated whenever Perseus acknowledges the entry, even when no
    glosses can be extracted.
    """
    label = f"[{idx+1}/{total}] {lemma}"

    async with semaphore:
        # ------------------------------------------------------------------
        # Stage 1: direct LSJ lookup
        # ------------------------------------------------------------------
        xml_bytes = await _fetch_xml(
            session, rate_limiter, lemma, max_retries, base_delay, label
        )

        if xml_bytes is not None:
            parsed = _parse_glosses(xml_bytes)
            if parsed is None:
                print(f"  {label} -> [parse error]")
                return (idx, "", _BROWSE_BASE + lemma)

            senses, formatted = parsed

            # Always persist XML when the fetch succeeds
            if xml_dir is not None:
                safe = re.sub(r"[^A-Za-z0-9_\-]", "_", lemma)
                (xml_dir / f"{safe}.xml").write_bytes(xml_bytes)

            if formatted:
                preview = formatted[:80].replace("\n", " | ")
                print(f"  {label}  senses={len(senses)}  {preview!r}")
                return (idx, formatted, _BROWSE_BASE + lemma)

        # ------------------------------------------------------------------
        # Stage 2: Morpheus fallback
        # ------------------------------------------------------------------
        print(f"  {label} -> no glosses, querying Morpheus …")
        candidates = await _resolve_lemmas(session, rate_limiter, stripped_bc)

        if not candidates:
            print(f"  {label} -> Morpheus returned no lemmas")
            url = _BROWSE_BASE + lemma if xml_bytes is not None else ""
            return (idx, "", url)

        for headword_bc in candidates:
            if headword_bc == lemma:
                continue
            hlabel = f"  {label} -> morph fallback bc={headword_bc}"
            fb_bytes = await _fetch_xml(
                session, rate_limiter, headword_bc, max_retries, base_delay, hlabel
            )
            if fb_bytes is None:
                continue
            parsed = _parse_glosses(fb_bytes)
            if parsed is None:
                continue
            senses, formatted = parsed
            if formatted:
                if xml_dir is not None:
                    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", headword_bc)
                    (xml_dir / f"{safe}.xml").write_bytes(fb_bytes)
                preview = formatted[:80].replace("\n", " | ")
                print(
                    f"  {label} -> resolved to bc={headword_bc}  "
                    f"senses={len(senses)}  {preview!r}"
                )
                # Record fallback: original lemma -> resolved headword
                fallback_log.append((lemma, headword_bc))
                return (idx, formatted, _BROWSE_BASE + headword_bc)

        print(f"  {label} -> all candidates returned no glosses")
        url = _BROWSE_BASE + lemma if xml_bytes is not None else ""
        return (idx, "", url)


# -- Async orchestrator -------------------------------------------------------

async def _enrich_async(
    df:                  pd.DataFrame,
    lemma_col:           str,
    bc_stripped_col:     str,
    url_col:             str,
    xml_dir:             Path | None,
    concurrency:         int,
    max_retries:         int,
    base_delay:          float,
    requests_per_second: float,
    meaning_col:         str,
    fallback_log_path:   Path,
) -> pd.DataFrame:
    # Only process rows where url is not yet populated
    needs_work = df[url_col].isna() | (df[url_col].astype(str).str.strip() == "")
    work_df    = df[needs_work]
    total      = len(work_df)

    print(f"  Rows to enrich: {total} (skipping {len(df) - total} already populated)")

    if total == 0:
        return df.copy()

    lemmas      = work_df[lemma_col].tolist()
    bc_stripped = work_df[bc_stripped_col].tolist()
    work_index  = work_df.index.tolist()   # original df indices

    results: list[tuple[str, str] | None] = [None] * total
    fallback_log: list[tuple[str, str]] = []   # (original_lemma, resolved_headword)

    semaphore    = asyncio.Semaphore(concurrency)
    rate_limiter = _RateLimiter(requests_per_second)
    connector    = aiohttp.TCPConnector(limit=concurrency)

    async with aiohttp.ClientSession(headers=_HEADERS, connector=connector) as session:
        tasks = [
            _fetch_one(
                session, semaphore, rate_limiter,
                i, total, str(lemmas[i]), str(bc_stripped[i]),
                xml_dir, max_retries, base_delay,
                fallback_log,
            )
            for i in range(total)
        ]
        completed = 0
        for coro in asyncio.as_completed(tasks):
            try:
                idx, meaning, url = await coro
                results[idx] = (meaning, url)
            except Exception as e:
                print(f"  [unexpected error]: {e}")
            completed += 1
            if completed % 50 == 0:
                filled = sum(1 for r in results if r is not None)
                print(
                    f"  --- progress: {completed}/{total} tasks done, "
                    f"{filled} results stored ---"
                )

    # Write fallback trace file
    if fallback_log:
        with fallback_log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"# Run enriched {total} lemmas\n")
            for orig, headword in fallback_log:
                fh.write(f"{orig}\t->\t{headword}\n")
        print(f"  Fallback trace: {len(fallback_log)} entries written to {fallback_log_path}")
    else:
        print("  Fallback trace: no Morpheus fallbacks used in this run")

    # Write results back into a copy of the full df, addressed by original index
    out = df.copy()
    for i, orig_idx in enumerate(work_index):
        meaning, url = results[i] if results[i] is not None else ("", "")
        out.at[orig_idx, meaning_col] = meaning
        out.at[orig_idx, url_col]     = url

    return out


# -- Public entry point -------------------------------------------------------

def enrich_dataframe_with_lsj(
    df: pd.DataFrame,
    lemma_col:           str               = "lemma_betacode",
    bc_stripped_col:     str               = "lemma_betacode_raw",
    meaning_col:         str               = "meaning",
    url_col:             str               = "url",
    xml_dir:             str | Path | None = "lsj_xml",
    fallback_log:        str | Path        = "lsj_fallback_log.txt",
    concurrency:         int               = 2,
    requests_per_second: float             = 1.0,
    max_retries:         int               = 6,
    base_delay:          float             = 2.0,
) -> pd.DataFrame:
    """
    Enrich *df* with LSJ meanings and Perseus URLs by fetching each lemma
    from the Perseus website.

    For every lemma in the DataFrame, the function:
      1. Makes an HTTP request to the Perseus LSJ XML endpoint.
      2. Saves the raw XML response to *xml_dir* (one file per lemma).
      3. Extracts top-level senses and writes them to *meaning_col*.
      4. Writes the Perseus browse URL to *url_col*.

    Rows where *url_col* is already populated are skipped, making the function
    safe to re-run after partial failures.

    When a lemma has no direct LSJ entry but Morpheus resolves it to a
    canonical headword, the meaning and URL of that headword are used and
    the mapping (lemma -> headword) is appended to *fallback_log* so future
    runs can use the correct XML file directly.

    If *meaning_col* or *url_col* do not yet exist in *df*, they are created
    automatically — so this works on a fresh DataFrame with no pre-existing
    output columns.

    Parameters
    ----------
    df                   : DataFrame containing Greek lemmas in Beta Code.
    lemma_col            : Column with Beta Code lemmas (with diacritics).
    bc_stripped_col      : Column with Beta Code lemmas (diacritics stripped),
                           used as the Morpheus fallback query.
    meaning_col          : Output column for formatted glosses
                           (created if absent; default: 'meaning').
    url_col              : Output column for Perseus browse URL
                           (created if absent; default: 'url').
                           Rows with a non-empty value here are skipped.
    xml_dir              : Folder to save raw XML files; None to skip saving.
    fallback_log         : Path to the txt file where Morpheus fallback
                           mappings are appended (TSV: original -> resolved).
    concurrency          : Max simultaneous open HTTP connections (default: 2).
                           Keep low — Perseus is a lightly resourced academic
                           server.
    requests_per_second  : Token-bucket throughput cap (default: 1.0 req/s).
                           Reduce to 0.5 if 429/503 responses keep appearing.
    max_retries          : Max retry attempts per request on hard errors
                           (default: 6).  429/503 pauses do NOT count toward
                           this limit.
    base_delay           : Base for full-jitter exponential backoff in seconds
                           (default: 2.0 → max delays of 2, 4, 8, 16, 32, 64 s).

    Returns
    -------
    pd.DataFrame
        A copy of *df* with *meaning_col* and *url_col* populated.
    """
    if lemma_col not in df.columns:
        raise ValueError(f"Column '{lemma_col}' not found in DataFrame.")
    if bc_stripped_col not in df.columns:
        raise ValueError(f"Column '{bc_stripped_col}' not found in DataFrame.")

    # Ensure output columns exist so the skip-check works even on first run
    out = df.copy()
    for col in (meaning_col, url_col):
        if col not in out.columns:
            out[col] = ""

    if xml_dir is not None:
        Path(xml_dir).mkdir(parents=True, exist_ok=True)

    return asyncio.run(
        _enrich_async(
            out,
            lemma_col, bc_stripped_col, url_col,
            Path(xml_dir) if xml_dir else None,
            concurrency, max_retries, base_delay,
            requests_per_second,
            meaning_col,
            Path(fallback_log),
        )
    )


# -- CLI usage ----------------------------------------------------------------

if __name__ == "__main__":
    import sys

    input_csv   = sys.argv[1] if len(sys.argv) > 1 else "merged_suffix.csv"
    output_csv  = sys.argv[2] if len(sys.argv) > 2 else "lsj_sense_enriched.csv"
    workers     = int(sys.argv[3])   if len(sys.argv) > 3 else 2
    req_per_sec = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

    df  = pd.read_csv(input_csv)
    df1 = enrich_dataframe_with_lsj(
        df,
        concurrency=workers,
        requests_per_second=req_per_sec,
    )
    df1.to_csv(output_csv, index=False)
    print(f"Saved to {output_csv}")
