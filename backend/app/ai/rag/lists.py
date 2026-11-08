"""Recover counted lists split by the knowledge chunk overlap."""

import re

from app.ai.providers.embedding import words

from .relevance import IGNORED


_HEADING = re.compile(r"(?<!\w)([2-9]|1\d|20)\s+([^.!?;/]{5,100}?)\s+(?=0?1(?:[.)])?\s+[^\W\d_])")
_QUERY_FILLER = IGNORED | {"liet", "ke", "gom", "can", "hay", "cho", "toi", "biet"}


def list_heading(question, text):
    terms = set(words(question))
    terms = {term for term in terms - _QUERY_FILLER if not term.isdigit()}
    for heading in _HEADING.finditer(text):
        heading_words = set(words(heading[2]))
        context = set(words(text[max(0, heading.start()-300):heading.start()]))
        if len(terms & heading_words) >= 2 and terms <= heading_words | context:
            return heading
    return None


def complete_list(heading, anchor, neighbors):
    text = anchor[heading.start():]
    for following in neighbors:
        tail = text.split()[-60:]
        head = following.split()
        overlap = next((size for size in range(min(len(tail),len(head)), 0, -1)
                        if tail[-size:] == head[:size]), 0)
        text += " " + " ".join(head[overlap:])
    markers = []
    start = heading.end()-heading.start()
    for number in range(1, int(heading[1])+1):
        match = re.search(rf"(?<!\w)0?{number}(?:[.)])?\s+(?=[^\W\d_])", text[start:])
        if not match:
            return None
        markers.append(start+match.start())
        start += match.end()
    ending = re.search(r"[.!?](?=\s|$)",text[start:])
    if not ending:
        return None
    end = start+ending.end()
    return text[:end], markers
