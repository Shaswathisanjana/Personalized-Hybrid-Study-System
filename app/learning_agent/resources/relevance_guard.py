import re


class ResourceRelevanceGuard:
    """
    Conservative metadata-based relevance filter.

    Search-query-derived resource topic tags are not used
    as independent evidence of relevance.

    These are prototype heuristics, not semantic validation.
    """

    LANGUAGE_TERMS = {
        "python": {"python"},
        "c": {"c"},
        "java": {"java"},
        "javascript": {"javascript", "js"},
        "c++": {"c++", "cpp"},
        "c#": {"c#", "csharp"},
        "ruby": {"ruby"},
        "go": {"golang"},
        "rust": {"rust"},
        "kotlin": {"kotlin"},
        "swift": {"swift"},
    }

    # Common search phrasing, not the learning topic itself.
    QUERY_FILLER = {
        "learn", "learning", "understand", "understanding",
        "introduction", "intro", "basics", "basic",
        "tutorial", "tutorials", "explained", "explain",
        "examples", "example", "for", "in", "of", "the",
        "a", "an", "and", "with", "using", "beginner",
        "beginners", "advanced", "programming",
    }

    @staticmethod
    def _tokens(text):
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    @classmethod
    def _mentioned_languages(cls, text):
        normalized = text.lower()
        found = set()

        # Detect C++ and C# before standalone C.
        for language, aliases in cls.LANGUAGE_TERMS.items():
            for alias in aliases:
                if language == "c":
                    pattern = r"(?<![a-z0-9])c(?![a-z0-9+#])"
                else:
                    pattern = (
                        r"(?<![a-z0-9])"
                        + re.escape(alias)
                        + r"(?![a-z0-9])"
                    )

                if re.search(pattern, normalized):
                    found.add(language)
                    break

        return found

    def is_relevant(self, concept_name, resource):
        query = concept_name.strip()

        if not query:
            return False

        title = resource.title or ""
        description = resource.description or ""
        actual_text = title + " " + description

        requested_languages = self._mentioned_languages(query)
        title_languages = self._mentioned_languages(title)

        # Reject resources explicitly advertised for a
        # different programming language.
        if (
            requested_languages
            and title_languages
            and requested_languages.isdisjoint(title_languages)
        ):
            return False

        # Remove query language names and generic search
        # phrasing to identify the actual learning topic.
        topic_query = query.lower()

        for language, aliases in self.LANGUAGE_TERMS.items():
            if language not in requested_languages:
                continue

            for alias in sorted(aliases, key=len, reverse=True):
                if language == "c":
                    pattern = r"(?<![a-z0-9])c(?![a-z0-9+#])"
                else:
                    pattern = (
                        r"(?<![a-z0-9])"
                        + re.escape(alias)
                        + r"(?![a-z0-9])"
                    )

                topic_query = re.sub(
                    pattern, " ", topic_query
                )

        topic_terms = (
            self._tokens(topic_query) - self.QUERY_FILLER
        )

        actual_terms = self._tokens(actual_text)

        # Explicitly supported related word forms.
        # Keep this mapping small and test each addition.
        RELATED_FORMS = {
            "recursion": {"recursive", "recursively"},
            "recursive": {"recursion", "recursively"},
        }

        expanded_actual_terms = set(actual_terms)

        for term in actual_terms:
            expanded_actual_terms.update(
                RELATED_FORMS.get(term, set())
            )

        if topic_terms:
            # Require actual evidence of the learning topic.
            if not (topic_terms & expanded_actual_terms):
                return False

        elif requested_languages:
            # For language-only queries such as "Python",
            # require evidence of that language.
            actual_languages = self._mentioned_languages(actual_text)

            if requested_languages.isdisjoint(actual_languages):
                return False

        else:
            # Avoid accepting a resource with no matching
            # evidence for a generic query.
            if not (self._tokens(query) & actual_terms):
                return False

        # Remove obvious non-educational Wikipedia results.
        if resource.source == "Wikipedia":
            lowered_title = title.lower()

            excluded_title_markers = (
                "(novel)",
                " novel",
                "(film)",
                "(album)",
                "(song)",
                "(disambiguation)",
            )

            if any(
                marker in lowered_title
                for marker in excluded_title_markers
            ):
                return False

        return True

