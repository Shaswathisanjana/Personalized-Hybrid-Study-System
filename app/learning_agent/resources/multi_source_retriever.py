from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit, urlunsplit


class MultiSourceResourceRetriever:
    """
    Combine independently retrieved educational resources.

    Each source implements:
        search(concept_name, max_results, target_level)

    Candidates are collected in round-robin order so
    the first retriever cannot monopolize the result pool.
    Final personalization is performed by the CACM ranker.
    """

    def __init__(self, retrievers):
        self.retrievers = list(retrievers)

        if not self.retrievers:
            raise ValueError(
                "At least one resource retriever is required."
            )

    @staticmethod
    def _url_key(url):
        parts = urlsplit(url.strip())

        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            parts.query,
            "",
        ))

    def search(
        self,
        concept_name,
        max_results=10,
        target_level=None,
    ):
        if not isinstance(concept_name, str) or not concept_name.strip():
            raise ValueError("concept_name cannot be empty.")

        if max_results <= 0:
            raise ValueError("max_results must be greater than zero.")

        source_results = []
        failures = []
        successful_sources = 0

        def retrieve(retriever):
            try:
                return list(retriever.search(concept_name=concept_name,
                    max_results=max_results,target_level=target_level)), None
            except Exception as exc:
                return [], f'{type(retriever).__name__}: {exc}'

        # Independent read-only sources run together. map retains input order,
        # so the existing deterministic round-robin ranking is unchanged.
        with ThreadPoolExecutor(max_workers=min(4,len(self.retrievers))) as pool:
            for candidates,error in pool.map(retrieve,self.retrievers):
                if error is not None:failures.append(error)
                else:
                    successful_sources += 1
                    source_results.append(candidates)

        if successful_sources == 0:
            raise RuntimeError(
                "All resource retrieval attempts failed: "
                + "; ".join(failures)
            )

        resources = []
        seen_urls = set()

        # One candidate from each source per round.
        for position in range(max_results):

            for candidates in source_results:

                if position >= len(candidates):
                    continue

                resource = candidates[position]
                key = self._url_key(resource.url)

                if key in seen_urls:
                    continue

                seen_urls.add(key)
                resources.append(resource)

                if len(resources) >= max_results:
                    return resources

        return resources
