"""Centralized configuration for all tunable constants.

All heuristic thresholds, sampling sizes, and page limits are defined here
to make tuning and future extension straightforward.
"""

# ---------------------------------------------------------------------------
# Text sampling / truncation
# ---------------------------------------------------------------------------
TEXT_TRUNCATE_LIMIT: int = 2000
"""Maximum characters to store in first_page_text fields."""

DOCX_SAMPLE_CHARS: int = 5000
"""Characters of paragraph text to read from DOCX before stopping."""

DOCX_TABLE_SAMPLE_COUNT: int = 5
"""Maximum tables to scan for text in DOCX files."""

TXT_BIB_SAMPLE_CHARS: int = 3000
"""Characters of text to scan for bibliographic metadata in TXT/MD."""

EPUB_DOCUMENT_SAMPLE_COUNT: int = 10
"""Maximum ITEM_DOCUMENT items to read from EPUB before stopping."""

EPUB_BIB_SAMPLE_CHARS: int = 3000
"""Characters of EPUB text to scan for bibliographic metadata."""

BIB_TEXT_SCAN_LINES: int = 15
"""Number of lines at start of text to scan for bibliographic info."""

# ---------------------------------------------------------------------------
# Page estimation
# ---------------------------------------------------------------------------
CHARS_PER_PAGE: int = 500
"""Characters per page for estimating page count of text-only files."""

SHORT_DOC_THRESHOLD: int = 50
"""Pages below this are considered short documents and read in full."""

LONG_DOC_HEAD_PAGES: int = 15
"""Number of pages to read from the start of a long document."""

LONG_DOC_TAIL_PAGES: int = 5
"""Number of pages to read from the end of a long document."""

# ---------------------------------------------------------------------------
# Scanned-PDF detection
# ---------------------------------------------------------------------------
SCANNED_TOTAL_CHARS_MAX: int = 8000
"""If total characters across read pages exceeds this, never flag as scanned."""

SCANNED_MIN_CHARS_PAGE: int = 25
"""A sampled page with fewer than this characters is considered "empty"."""

SCANNED_EMPTY_RATIO: float = 0.66
"""Fraction of sampled pages that must be empty to flag as scanned."""

SCANNED_DENSITY_THRESHOLD: float = 12.0
"""Average chars per sampled page below this triggers scanned flag (if >3 pages read)."""

SCANNED_TOTAL_CHARS_HARD: int = 50
"""If total characters is below this, always flag as scanned."""

# ---------------------------------------------------------------------------
# PDF fallback
# ---------------------------------------------------------------------------
PDF_FALLBACK_TEXT_CHARS: int = 500
"""If PyPDF2 extracts fewer than this chars and pdfplumber is available, try fallback."""

# ---------------------------------------------------------------------------
# Citation thresholds
# ---------------------------------------------------------------------------
MONOGRAPH_PAGE_THRESHOLD: int = 200
"""Documents above this page count are typed as monographs [M] in GB/T 7714."""

# ---------------------------------------------------------------------------
# Metadata extraction heuristics
# ---------------------------------------------------------------------------
META_TITLE_MIN_LEN: int = 10
"""Minimum character length for a candidate title extracted from first-page text."""

META_TITLE_MAX_LEN: int = 200
"""Maximum character length for a candidate title extracted from first-page text."""

META_TITLE_CANDIDATE_LINES: int = 3
"""Number of first-page lines to consider as title candidates."""
