"""Prerequisite Graph: Directed Acyclic Graph (DAG) management of curriculum dependencies."""

from collections import defaultdict, deque
from typing import List, Dict, Set, Optional

from cognitive_learning_agent.models.schemas import PrerequisiteRelation, ConceptMasteryItem


class PrerequisiteGraph:
    """Manages prerequisite dependencies between learning concepts using DAG traversal."""

    def __init__(self, relations: Optional[List[PrerequisiteRelation]] = None):
        self.adj = defaultdict(set)  # prereq -> set of dependent concepts
        self.in_degree = defaultdict(int)
        self.all_nodes: Set[str] = set()

        if relations:
            for r in relations:
                self.add_prerequisite(r.concept_name, r.prerequisite_name)

    def add_prerequisite(self, concept_name: str, prerequisite_name: str):
        """Register that prerequisite_name must be learned before concept_name."""
        self.all_nodes.add(concept_name)
        self.all_nodes.add(prerequisite_name)

        if concept_name not in self.adj[prerequisite_name]:
            self.adj[prerequisite_name].add(concept_name)
            self.in_degree[concept_name] += 1
            if prerequisite_name not in self.in_degree:
                self.in_degree[prerequisite_name] = 0

    def add_concept(self, concept_name: str):
        """Add an independent concept if not already tracked."""
        self.all_nodes.add(concept_name)
        if concept_name not in self.in_degree:
            self.in_degree[concept_name] = 0

    def topological_sort(self) -> List[str]:
        """Compute valid linear learning sequence respecting all prerequisites."""
        in_deg = {node: self.in_degree[node] for node in self.all_nodes}
        queue = deque([node for node in self.all_nodes if in_deg[node] == 0])
        ordered = []

        while queue:
            curr = queue.popleft()
            ordered.append(curr)

            for neighbor in self.adj[curr]:
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        # In case of cycles, append remaining nodes
        if len(ordered) < len(self.all_nodes):
            for node in self.all_nodes:
                if node not in ordered:
                    ordered.append(node)

        return ordered

    def get_unmastered_prerequisites(
        self,
        concept_name: str,
        masteries: Dict[str, ConceptMasteryItem],
        mastery_threshold: float = 0.60,
    ) -> List[str]:
        """Identify which prerequisites of concept_name have not yet achieved required mastery."""
        # Find all direct prerequisites (nodes that point to concept_name)
        direct_prereqs = [
            prereq for prereq, dependents in self.adj.items() if concept_name in dependents
        ]

        unmastered = []
        for p in direct_prereqs:
            m_item = masteries.get(p)
            if m_item is None or m_item.mastery_score < mastery_threshold:
                unmastered.append(p)

        return unmastered

    def get_immediate_prerequisites(self, concept_name: str) -> List[str]:
        """Return list of direct prerequisites for a concept."""
        return [prereq for prereq, dependents in self.adj.items() if concept_name in dependents]
