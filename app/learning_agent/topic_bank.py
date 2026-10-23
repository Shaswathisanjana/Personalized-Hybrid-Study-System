from app.cognitive.concept_identity import concept_id
from dataclasses import dataclass


@dataclass(frozen=True)
class LearningTopic:
    name: str
    category: str
    difficulty: str
    prerequisites: tuple[str, ...] = ()


TOPICS = (
    # Python
    LearningTopic("Python Basics", "Python", "easy"),
    LearningTopic("Python Variables and Data Types", "Python", "easy", ("Python Basics",)),
    LearningTopic("Python Conditionals", "Python", "easy", ("Python Basics",)),
    LearningTopic("Python Loops", "Python", "easy", ("Python Conditionals",)),
    LearningTopic("Python Functions", "Python", "easy", ("Python Basics",)),
    LearningTopic("Python Lists", "Python", "easy", ("Python Basics",)),
    LearningTopic("Python Dictionaries", "Python", "easy", ("Python Basics",)),
    LearningTopic("Python Recursion", "Python", "medium", ("Python Functions",)),
    LearningTopic("Python OOP", "Python", "medium", ("Python Functions",)),
    LearningTopic("Python File Handling", "Python", "medium", ("Python Basics",)),
    LearningTopic("Python Exception Handling", "Python", "medium", ("Python Functions",)),

    # Data Structures and Algorithms
    LearningTopic("Time and Space Complexity", "DSA", "easy", ("Python Basics",)),
    LearningTopic("Arrays", "DSA", "easy", ("Python Lists",)),
    LearningTopic("Strings", "DSA", "easy", ("Python Basics",)),
    LearningTopic("Searching Algorithms", "DSA", "medium", ("Arrays",)),
    LearningTopic("Sorting Algorithms", "DSA", "medium", ("Arrays",)),
    LearningTopic("Linked Lists", "DSA", "medium", ("Python Functions",)),
    LearningTopic("Stacks", "DSA", "medium", ("Arrays",)),
    LearningTopic("Queues", "DSA", "medium", ("Arrays",)),
    LearningTopic("Hashing", "DSA", "medium", ("Python Dictionaries",)),
    LearningTopic("Trees", "DSA", "medium", ("Python Recursion",)),
    LearningTopic("Graphs", "DSA", "hard", ("Trees",)),
    LearningTopic("Dynamic Programming", "DSA", "hard", ("Python Recursion",)),

    # Artificial Intelligence and Machine Learning
    LearningTopic("Introduction to AI", "AI and ML", "easy"),
    LearningTopic("Introduction to Machine Learning", "AI and ML", "easy", ("Introduction to AI",)),
    LearningTopic("Data Preprocessing", "AI and ML", "easy", ("Introduction to Machine Learning",)),
    LearningTopic("Supervised Learning", "AI and ML", "medium", ("Introduction to Machine Learning",)),
    LearningTopic("Unsupervised Learning", "AI and ML", "medium", ("Introduction to Machine Learning",)),
    LearningTopic("Regression", "AI and ML", "medium", ("Supervised Learning",)),
    LearningTopic("Classification", "AI and ML", "medium", ("Supervised Learning",)),
    LearningTopic("Model Evaluation Metrics", "AI and ML", "medium", ("Supervised Learning",)),
    LearningTopic("Neural Networks", "AI and ML", "medium", ("Introduction to Machine Learning",)),
    LearningTopic("Deep Learning", "AI and ML", "hard", ("Neural Networks",)),
    LearningTopic("Natural Language Processing", "AI and ML", "hard", ("Introduction to Machine Learning",)),
    LearningTopic("Computer Vision", "AI and ML", "hard", ("Deep Learning",)),
    LearningTopic("Reinforcement Learning", "AI and ML", "hard", ("Introduction to Machine Learning",)),

    # Databases
    LearningTopic("Database Fundamentals", "Databases", "easy"),
    LearningTopic("SQL Basics", "Databases", "easy", ("Database Fundamentals",)),
    LearningTopic("SQL Joins", "Databases", "medium", ("SQL Basics",)),
    LearningTopic("SQL Aggregation", "Databases", "medium", ("SQL Basics",)),
    LearningTopic("Database Normalization", "Databases", "medium", ("Database Fundamentals",)),
    LearningTopic("Transactions and ACID", "Databases", "medium", ("Database Fundamentals",)),
    LearningTopic("Database Indexing", "Databases", "hard", ("SQL Basics",)),

    # Core Computer Science
    LearningTopic("Operating System Fundamentals", "Core CS", "easy"),
    LearningTopic("Processes and Threads", "Core CS", "medium", ("Operating System Fundamentals",)),
    LearningTopic("CPU Scheduling", "Core CS", "medium", ("Processes and Threads",)),
    LearningTopic("Deadlocks", "Core CS", "medium", ("Processes and Threads",)),
    LearningTopic("Computer Networks Fundamentals", "Core CS", "easy"),
    LearningTopic("OSI Model", "Core CS", "easy", ("Computer Networks Fundamentals",)),
    LearningTopic("TCP and UDP", "Core CS", "medium", ("Computer Networks Fundamentals",)),
)


class LearningTopicBank:
    def __init__(self):
        self._topics = {concept_id(topic.name): topic for topic in TOPICS}

        if len(self._topics) != len(TOPICS):
            raise ValueError("Duplicate topic names detected.")

        for topic in TOPICS:
            for prerequisite in topic.prerequisites:
                if concept_id(prerequisite) not in self._topics:
                    raise ValueError(
                        f"Unknown prerequisite {prerequisite!r} "
                        f"for {topic.name!r}."
                    )

    def all_topics(self) -> list[LearningTopic]:
        return list(TOPICS)

    def categories(self) -> list[str]:
        return sorted({topic.category for topic in TOPICS})

    def by_category(self, category: str) -> list[LearningTopic]:
        return [
            topic for topic in TOPICS
            if topic.category.casefold() == category.strip().casefold()
        ]

    def get(self, name: str) -> LearningTopic | None:
        return self._topics.get(concept_id(name)) if name.strip() else None

    def search(self, query: str) -> list[LearningTopic]:
        query = query.strip().casefold()

        if not query:
            return self.all_topics()

        return [
            topic for topic in TOPICS
            if query in topic.name.casefold()
            or query in topic.category.casefold()
        ]

    def prerequisites_for(self, name: str) -> list[LearningTopic]:
        topic = self.get(name)

        if topic is None:
            return []

        return [
            self._topics[concept_id(prerequisite)]
            for prerequisite in topic.prerequisites
        ]
