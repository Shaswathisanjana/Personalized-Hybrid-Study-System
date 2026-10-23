import html
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen

from dotenv import load_dotenv

from app.learning_agent.resources.difficulty_estimator import (
    ResourceDifficultyEstimator,
)

from app.learning_agent.resources.models import (
    LearningResource,
)


load_dotenv()


class YouTubeResourceRetriever:
    """
    Retrieves real public educational videos from YouTube.

    Pipeline:

        concept + target difficulty
                ↓
        difficulty-aware YouTube search
                ↓
        candidate videos
                ↓
        metadata cleanup
                ↓
        independent difficulty estimation
                ↓
        LearningResource objects

    IMPORTANT:
    The requested target difficulty affects the search query,
    but it does NOT automatically determine the difficulty
    assigned to a returned video.

    Each returned video is independently classified by
    ResourceDifficultyEstimator.

    Final personalized selection is handled separately by
    LearningResourceRanker.
    """

    SEARCH_URL = (
        "https://www.googleapis.com/youtube/v3/search"
    )

    VIDEOS_URL = (
        "https://www.googleapis.com/youtube/v3/videos"
    )

    VALID_LEVELS = {
        "easy",
        "medium",
        "hard",
    }

    def __init__(
        self,
        api_key: str | None = None,
        difficulty_estimator=None,
    ):
        self.api_key = (
            api_key
            or os.getenv("YOUTUBE_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "YOUTUBE_API_KEY was not found."
            )

        self.difficulty_estimator = (
            difficulty_estimator
            if difficulty_estimator is not None
            else ResourceDifficultyEstimator()
        )

    # ==================================================
    # PUBLIC METHOD
    # ==================================================

    def search(
        self,
        concept_name: str,
        max_results: int = 8,
        target_level: str | None = None,
    ) -> list[LearningResource]:
        """
        Retrieve candidate educational videos.

        target_level may be:
            easy
            medium
            hard

        If target_level is supplied, it changes the search
        query so that the candidate pool is more suitable
        for the student's current CACM state.

        Difficulty is still independently estimated after
        retrieval.
        """

        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if max_results <= 0:
            raise ValueError(
                "max_results must be greater than zero."
            )

        if target_level is not None:

            target_level = (
                target_level
                .strip()
                .lower()
            )

            if target_level not in self.VALID_LEVELS:
                raise ValueError(
                    "target_level must be easy, "
                    "medium, hard, or None."
                )

        max_results = min(
            max_results,
            50,
        )

        # ----------------------------------------------
        # BUILD DIFFICULTY-AWARE SEARCH QUERY
        # ----------------------------------------------

        search_query = self._build_search_query(
            concept_name=concept_name,
            target_level=target_level,
        )

        search_data = self._search_videos(
            query=search_query,
            max_results=max_results,
        )

        candidates = (
            self._extract_search_candidates(
                search_data
            )
        )

        if not candidates:
            return []

        video_ids = [
            candidate["video_id"]
            for candidate in candidates
        ]

        statistics = self._get_video_statistics(
            video_ids
        )

        resources = []

        for candidate in candidates:

            video_id = candidate[
                "video_id"
            ]

            video_statistics = statistics.get(
                video_id,
                {},
            )

            view_count = self._safe_int(
                video_statistics.get(
                    "viewCount"
                )
            )

            # ------------------------------------------
            # INDEPENDENT DIFFICULTY ESTIMATION
            # ------------------------------------------

            difficulty = (
                self.difficulty_estimator.estimate(
                    title=candidate["title"],
                    description=candidate[
                        "description"
                    ],
                )
            )

            resource = LearningResource(
                title=candidate["title"],
                url=(
                    "https://www.youtube.com/watch"
                    f"?v={video_id}"
                ),
                resource_type="video",
                description=candidate[
                    "description"
                ],
                source=(
                    "YouTube - "
                    + candidate["channel_title"]
                ),
                difficulty=difficulty,
                view_count=view_count,
                topics=[concept_name],
            )

            resources.append(
                resource
            )

        return resources

    # ==================================================
    # DIFFICULTY-AWARE QUERY
    # ==================================================

    @staticmethod
    def _build_search_query(
        concept_name: str,
        target_level: str | None,
    ) -> str:
        """
        Construct a search query appropriate for the
        student's current target learning level.

        These query expansions are transparent project
        heuristics.
        """

        if target_level == "easy":

            return (
                f"{concept_name} "
                f"beginner basics explained tutorial"
            )

        if target_level == "medium":

            return (
                f"{concept_name} "
                f"practice examples implementation tutorial"
            )

        if target_level == "hard":

            return (
                f"{concept_name} "
                f"advanced complexity challenging problems"
            )

        # Generic fallback when no cognitive level
        # has been supplied.
        return (
            f"{concept_name} tutorial educational"
        )

    # ==================================================
    # SEARCH REQUEST
    # ==================================================

    def _search_videos(
        self,
        query: str,
        max_results: int,
    ) -> dict:

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "safeSearch": "strict",
            "relevanceLanguage": "en",
            "key": self.api_key,
        }

        return self._request_json(
            self.SEARCH_URL,
            params,
        )

    # ==================================================
    # VIDEO STATISTICS
    # ==================================================

    def _get_video_statistics(
        self,
        video_ids: list[str],
    ) -> dict[str, dict]:

        if not video_ids:
            return {}

        params = {
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }

        data = self._request_json(
            self.VIDEOS_URL,
            params,
        )

        result = {}

        for item in data.get(
            "items",
            [],
        ):

            video_id = item.get(
                "id"
            )

            if not video_id:
                continue

            result[video_id] = (
                item.get(
                    "statistics",
                    {},
                )
            )

        return result

    # ==================================================
    # CONVERT SEARCH RESULTS
    # ==================================================

    @staticmethod
    def _extract_search_candidates(
        data: dict,
    ) -> list[dict]:

        candidates = []

        for item in data.get(
            "items",
            [],
        ):

            video_id = (
                item.get(
                    "id",
                    {},
                )
                .get(
                    "videoId"
                )
            )

            snippet = item.get(
                "snippet",
                {},
            )

            if not video_id:
                continue

            raw_title = snippet.get(
                "title",
                "",
            )

            raw_description = snippet.get(
                "description",
                "",
            )

            raw_channel = snippet.get(
                "channelTitle",
                "Unknown channel",
            )

            # Decode YouTube HTML entities.
            title = html.unescape(
                raw_title
            ).strip()

            description = html.unescape(
                raw_description
            ).strip()

            channel_title = html.unescape(
                raw_channel
            ).strip()

            if not title:
                continue

            candidates.append(
                {
                    "video_id": video_id,
                    "title": title,
                    "description": description,
                    "channel_title": (
                        channel_title
                        or "Unknown channel"
                    ),
                }
            )

        return candidates

    # ==================================================
    # HTTP
    # ==================================================

    @staticmethod
    def _request_json(
        base_url: str,
        params: dict,
    ) -> dict:

        url = (
            base_url
            + "?"
            + urlencode(params)
        )

        try:

            with urlopen(
                url,
                timeout=10,
            ) as response:

                return json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

        except Exception as exc:

            raise RuntimeError(
                "YouTube resource retrieval failed: "
                f"{exc}"
            ) from exc

    # ==================================================
    # HELPERS
    # ==================================================

    @staticmethod
    def _safe_int(
        value,
    ) -> int | None:

        if value is None:
            return None

        try:
            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None