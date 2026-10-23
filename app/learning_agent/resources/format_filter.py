from typing import Sequence


RESOURCE_FORMATS = (
    "All Resources",
    "Videos",
    "Articles",
    "Documentation",
)


def filter_ranked_resources(
    ranked_resources: Sequence,
    selected_format: str,
) -> list:
    """
    Filter already-ranked resources by educational format.

    This function does not modify ranking scores,
    recalculate relevance, or change the original list.
    """

    if selected_format not in RESOURCE_FORMATS:
        raise ValueError(
            f"Unsupported resource format: {selected_format}"
        )

    if selected_format == "All Resources":
        return list(ranked_resources)

    accepted_types = {
        "Videos": {"video"},
        "Articles": {"article", "tutorial", "webpage"},
        "Documentation": {"documentation"},
    }[selected_format]

    return [
        item
        for item in ranked_resources
        if item.resource.resource_type in accepted_types
    ]
