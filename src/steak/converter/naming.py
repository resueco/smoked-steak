import re

# A separate lossless quality tag used by common release folder naming schemes,
# for example ``[24B-44.1kHz]``.
QUALITY_TAG_RE = re.compile(
    r"\[\s*(?P<bit_depth>\d{1,2})\s*B\s*-\s*(?P<sample_rate>\d+(?:\.\d+)?)\s*kHz\s*\]",
    flags=re.IGNORECASE,
)


def format_quality_tag(bit_depth: int, sample_rate: int) -> str:
    """Format a lossless bit-depth/sample-rate folder tag."""
    sample_rate_khz = f"{sample_rate / 1000:g}"
    return f"[{bit_depth}B-{sample_rate_khz}kHz]"


def remove_quality_tags(foldername: str) -> str:
    """Remove lossless quality tags and the whitespace immediately before them."""
    return re.sub(rf"\s*{QUALITY_TAG_RE.pattern}", "", foldername, flags=re.IGNORECASE)
