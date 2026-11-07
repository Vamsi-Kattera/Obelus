"""Cut a contract into overlapping character windows, remembering where each came from."""


def make_chunks(text, size=1200, step=600):
    """Return a list of (start, end, chunk_text). Overlap = size - step."""
    if size <= 0 or step <= 0:
        raise ValueError("size and step must be positive")
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append((start, end, text[start:end]))
        if end == len(text):
            break
        start += step
    return chunks


def overlaps(a_start, a_end, b_start, b_end):
    """True if the two character ranges share at least one character."""
    return a_start < b_end and b_start < a_end
