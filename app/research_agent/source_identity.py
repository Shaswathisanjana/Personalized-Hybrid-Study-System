"""Conservative publication deduplication and exact-source cache identities."""
from dataclasses import asdict
import hashlib
import json
from urllib.parse import urlsplit


def source_keys(paper):
    keys = set()
    if getattr(paper, 'doi', ''):
        doi = paper.doi.strip().casefold()
        for prefix in ('https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'doi:'):
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
                break
        keys.add('doi:' + doi)
    if paper.paper_id:
        keys.add("id:" + paper.source.casefold() + ":" + paper.paper_id.strip().casefold())
    if paper.url:
        parts = urlsplit(paper.url)
        host = parts.netloc.casefold()
        path = parts.path.rstrip("/")
        if host in ("doi.org", "dx.doi.org"):
            keys.add("doi:" + path.lstrip("/").casefold())
        else:
            # Paths and query strings can be case-sensitive. Ignore fragments.
            # Shared generic landing pages may describe different publications.
            # Without a common ID/DOI, require the same title too.
            keys.add("url:" + host + path + ("?" + parts.query if parts.query else "")
                     + "|title:" + " ".join(paper.title.casefold().split()))
    if not keys:
        keys.add("title:" + " ".join(paper.title.casefold().split()))
    return keys


def merge_sources(papers, incoming, validator):
    """Retain distinct publications; replace an unusable duplicate with usable text."""
    for paper in incoming:
        match = next((i for i, existing in enumerate(papers)
                      if source_keys(existing) & source_keys(paper)), None)
        if match is None:
            papers.append(paper)
        elif (not validator.validate(papers[match].abstract, papers[match].title).is_usable
              and validator.validate(paper.abstract, paper.title).is_usable):
            papers[match] = paper
    return papers


def source_fingerprint(paper):
    """Cache only the exact retrieved source, including its abstract and metadata."""
    data = asdict(paper)
    if not data.get('doi'):
        data.pop('doi', None)  # Preserve cache keys from pre-DOI snapshots.
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
