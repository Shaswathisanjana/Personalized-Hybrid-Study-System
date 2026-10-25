import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity


def cluster_sentences(embeddings):
    """
    Group semantically similar limitation/evidence sentences
    using BGE embeddings.
    """

    n = len(embeddings)

    if n == 0:
        return []

    if n == 1:
        return [0]

    n_clusters = max(2, min(6, round(np.sqrt(n))))
    n_clusters = min(n_clusters, n)

    model = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric="cosine",
        linkage="average",
    )

    return model.fit_predict(embeddings).tolist()


def rank_by_query(query_embedding, embeddings):
    """
    Calculate semantic relevance between the research topic
    and each evidence sentence.
    """

    if len(embeddings) == 0:
        return []

    scores = cosine_similarity(
        np.asarray(query_embedding).reshape(1, -1),
        np.asarray(embeddings),
    )[0]

    return scores.tolist()


def build_evidence_clusters(
    candidate_sentences,
    sentence_embeddings,
    query_embedding,
    source_indices=None,
):
    """
    Build semantic evidence clusters.

    Each evidence item retains its original paper index.
    This allows the system to calculate how many UNIQUE
    papers support a semantic evidence theme.

    This function does NOT generate research-gap text.
    """

    if not candidate_sentences:
        return []

    if source_indices is None:
        source_indices = [None] * len(candidate_sentences)

    clusters = cluster_sentences(sentence_embeddings)

    relevance_scores = rank_by_query(
        query_embedding,
        sentence_embeddings,
    )

    evidence = []

    for i, sentence in enumerate(candidate_sentences):

        evidence.append({
            "sentence": sentence,
            "cluster_id": int(clusters[i]),
            "relevance": round(
                float(relevance_scores[i]),
                4,
            ),
            "paper_index": source_indices[i],
        })

    cluster_ids = sorted(
        set(item["cluster_id"] for item in evidence)
    )

    cluster_results = []

    for cluster_id in cluster_ids:

        members = [
            item
            for item in evidence
            if item["cluster_id"] == cluster_id
        ]

        evidence_count = len(members)

        # ---------------------------------------------------------
        # UNIQUE PAPER COUNT
        # ---------------------------------------------------------

        paper_indices = {
            item["paper_index"]
            for item in members
            if item["paper_index"] is not None
        }

        unique_paper_count = len(paper_indices)

        # ---------------------------------------------------------
        # RELEVANCE
        # ---------------------------------------------------------

        average_relevance = float(
            np.mean(
                [item["relevance"] for item in members]
            )
        )

        max_relevance = max(
            item["relevance"]
            for item in members
        )

        # ---------------------------------------------------------
        # SORT EVIDENCE BY RELEVANCE
        # ---------------------------------------------------------

        members = sorted(
            members,
            key=lambda x: x["relevance"],
            reverse=True,
        )

        # ---------------------------------------------------------
        # RECURRENCE
        #
        # Recurrence is based on UNIQUE PAPERS,
        # not number of sentences.
        # ---------------------------------------------------------

        total_unique_papers = len(
            set(
                index
                for index in source_indices
                if index is not None
            )
        )

        recurrence_factor = (
            unique_paper_count
            / max(1, total_unique_papers)
        )

        recurrence_factor = min(
            recurrence_factor,
            1.0,
        )

        # ---------------------------------------------------------
        # CLUSTER PRIORITY
        # ---------------------------------------------------------

        cluster_priority = (
            0.75 * average_relevance
            + 0.25 * recurrence_factor
        )

        cluster_results.append({

            "cluster_id":
                cluster_id,

            "evidence_count":
                evidence_count,

            "unique_paper_count":
                unique_paper_count,

            "average_relevance":
                round(
                    average_relevance,
                    4,
                ),

            "max_relevance":
                round(
                    float(max_relevance),
                    4,
                ),

            "recurrence_factor":
                round(
                    float(recurrence_factor),
                    4,
                ),

            "cluster_priority":
                round(
                    float(cluster_priority),
                    4,
                ),

            "evidence":
                members,
        })

    # Highest-priority evidence themes first
    cluster_results.sort(
        key=lambda x: x["cluster_priority"],
        reverse=True,
    )

    return cluster_results


def build_gap_candidates(
    candidate_sentences,
    sentence_embeddings,
    query_embedding,
    source_indices=None,
):
    """
    Backward-compatible wrapper.

    Converts semantic evidence clusters into
    flattened candidate records.
    """

    clusters = build_evidence_clusters(
        candidate_sentences,
        sentence_embeddings,
        query_embedding,
        source_indices,
    )

    gap_candidates = []

    for cluster in clusters:

        for item in cluster["evidence"]:

            gap_candidates.append({

                "sentence":
                    item["sentence"],

                "cluster":
                    cluster["cluster_id"],

                "relevance":
                    item["relevance"],

                "recurrence":
                    cluster["unique_paper_count"],

                "unique_paper_count":
                    cluster["unique_paper_count"],

                "gap_priority":
                    cluster["cluster_priority"],

            })

    return (
        gap_candidates,
        [
            item["cluster_id"]
            for item in clusters
        ],
    )