from app.research_agent.abstract_quality_validator import (
    AbstractQualityValidator,
)


def main():

    validator = AbstractQualityValidator()

    cases = [
        {
            "name": "Empty abstract",
            "title": "Example Research Paper",
            "abstract": "",
            "expected": "reject",
        },
        {
            "name": "Actual problematic abstract",
            "title": "Deep Learning in Medical Image Classification",
            "abstract": (
                "Deep Learning in Medical Image Classification - 1"
            ),
            "expected": "reject",
        },
        {
            "name": "Meaningful research abstract",
            "title": "Medical Image Classification Using CNN",
            "abstract": (
                "Medical image classification is an important task "
                "in computer-aided diagnosis. This study proposes "
                "a convolutional neural network for identifying "
                "disease patterns in medical images. The proposed "
                "approach is evaluated using a labelled dataset "
                "containing multiple diagnostic categories. "
                "Classification accuracy, precision, recall, and "
                "F1-score are used to assess performance. "
                "The experimental results demonstrate the "
                "effectiveness of the proposed classification "
                "approach."
            ),
            "expected": "accept",
        },
        {
            "name": "Unusually short abstract",
            "title": "Transformer Research",
            "abstract": (
                "We investigate transformer-based classification "
                "using medical images."
            ),
            "expected": "review",
        },
    ]

    for case in cases:

        result = validator.validate(
            abstract=case["abstract"],
            title=case["title"],
        )

        print("\nTEST:", case["name"])
        print("Status:", result.status)
        print("Usable:", result.is_usable)
        print("Word count:", result.word_count)
        print("Reason:", result.reason)

        assert result.status == case["expected"], (
            f"{case['name']}: expected {case['expected']}, "
            f"received {result.status}"
        )

        assert result.is_usable == (
            case["expected"] == "accept"
        )

    print(
        "\nTEST PASSED: All four abstract quality "
        "validation scenarios behave correctly."
    )


if __name__ == "__main__":
    main()
