"""
analysis/genealogy.py

Attack Genealogy Tracker — Novel Mutation Lineage Analysis.

Motivation:
  Red-team platforms typically report *which* prompts succeeded but not
  *how* they were derived. Understanding the mutation chain from an initial
  seed to a successful jailbreak reveals which transformations are most
  effective, which seeds are most productive, and how "attack fitness"
  evolves through mutation.

  This module tracks the complete genealogy of adversarial prompt generation,
  enabling:
    1. **Mutation Efficiency Analysis**: Which mutation operators (encoding,
       register shift, template substitution) produce the most jailbreaks per
       application?
    2. **Lineage Tracing**: Full ancestry chain from seed → mutant → jailbreak.
    3. **Attack Family Trees**: Visualizable trees showing how seeds branch
       into mutation variants.
    4. **Shortest Successful Chain**: Minimum mutations needed to jailbreak.
    5. **Crossover Potential**: Which seeds produce mutations that work across
       multiple categories?

Novel metrics:
  - Mutation Efficiency (ME): jailbreak_rate per mutation type
  - Generational Fitness Gain: improvement in jailbreak rate per generation
  - Seed Productivity Score: weighted jailbreak yield per seed prompt
  - Lineage Depth Distribution: histogram of successful chain lengths

References:
  Inspired by:
    - Genetic algorithm frameworks (Holland, 1975)
    - GCG: Zou et al. (2023). Universal and Transferable Adversarial Attacks.
    - AutoDAN: Liu et al. (2023). AutoDAN: Interpretable Gradient-Based Adversarial Attacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import math


# ── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class PromptNode:
    """
    A node in the attack genealogy tree.

    Each node represents one prompt in the mutation lineage.
    """
    node_id: str                          # Unique ID (e.g. "seed-0", "gen1-0-3")
    prompt: str                           # The prompt text
    parent_id: Optional[str]             # Parent node ID (None for seeds)
    mutation_applied: Optional[str]      # Name of the mutation operator
    generation: int                      # 0 = seed, 1 = first mutation, etc.
    is_jailbroken: bool = False
    jailbreak_score: float = 0.0
    model_tested: Optional[str] = None
    children: list[str] = field(default_factory=list)  # child node IDs

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "mutation_applied": self.mutation_applied,
            "is_jailbroken": self.is_jailbroken,
            "jailbreak_score": round(self.jailbreak_score, 3),
            "prompt_preview": self.prompt[:100] + "..." if len(self.prompt) > 100 else self.prompt,
            "n_children": len(self.children),
        }


@dataclass
class GenealogyResult:
    """Complete genealogy analysis for an evaluation run."""
    nodes: dict[str, PromptNode]              # All nodes by ID
    successful_lineages: list[list[str]]      # Node ID chains leading to jailbreaks
    mutation_efficiency: dict[str, float]     # ME per mutation operator
    seed_productivity: dict[str, float]       # Yield per seed
    generational_fitness: dict[int, float]    # ASR per generation
    shortest_chain_length: Optional[int]      # Min mutations to success
    avg_successful_chain_length: float
    most_effective_mutation: Optional[str]
    most_productive_seed: Optional[str]

    def to_dict(self) -> dict:
        return {
            "n_nodes": len(self.nodes),
            "n_successful_lineages": len(self.successful_lineages),
            "mutation_efficiency": {
                k: round(v, 4) for k, v in self.mutation_efficiency.items()
            },
            "seed_productivity": {
                k: round(v, 4) for k, v in self.seed_productivity.items()
            },
            "generational_fitness": {
                str(k): round(v, 4) for k, v in self.generational_fitness.items()
            },
            "shortest_chain_length": self.shortest_chain_length,
            "avg_successful_chain_length": round(self.avg_successful_chain_length, 2),
            "most_effective_mutation": self.most_effective_mutation,
            "most_productive_seed": self.most_productive_seed,
            "successful_lineages": [
                self._format_lineage(chain)
                for chain in self.successful_lineages[:5]  # Top 5
            ],
        }

    def _format_lineage(self, chain: list[str]) -> dict:
        return {
            "chain_length": len(chain),
            "steps": [
                {
                    "node_id": nid,
                    "mutation": self.nodes[nid].mutation_applied,
                    "jailbroken": self.nodes[nid].is_jailbroken,
                }
                for nid in chain if nid in self.nodes
            ],
        }


# ── Genealogy Tree Builder ───────────────────────────────────────────────────

class GenealogyTree:
    """
    Builds and analyzes the complete attack genealogy tree.

    Usage:
        tree = GenealogyTree()
        # Register seed prompts
        for i, prompt in enumerate(seeds):
            tree.add_seed(f"seed-{i}", prompt)
        # Register mutations
        for parent_id, child_prompt, mutation_name, is_jb, score in mutations:
            child_id = tree.add_mutation(parent_id, child_prompt, mutation_name, is_jb, score)
        # Analyze
        result = tree.analyze()
    """

    def __init__(self):
        self._nodes: dict[str, PromptNode] = {}

    def add_seed(
        self,
        node_id: str,
        prompt: str,
        is_jailbroken: bool = False,
        jailbreak_score: float = 0.0,
        model: Optional[str] = None,
    ) -> str:
        """Register a seed (generation 0) prompt."""
        node = PromptNode(
            node_id=node_id,
            prompt=prompt,
            parent_id=None,
            mutation_applied=None,
            generation=0,
            is_jailbroken=is_jailbroken,
            jailbreak_score=jailbreak_score,
            model_tested=model,
        )
        self._nodes[node_id] = node
        return node_id

    def add_mutation(
        self,
        parent_id: str,
        prompt: str,
        mutation_applied: str,
        is_jailbroken: bool = False,
        jailbreak_score: float = 0.0,
        model: Optional[str] = None,
        child_id: Optional[str] = None,
    ) -> str:
        """Register a mutated prompt as a child of parent_id."""
        parent = self._nodes.get(parent_id)
        generation = (parent.generation + 1) if parent else 1

        if child_id is None:
            child_id = f"gen{generation}-{len(self._nodes)}"

        node = PromptNode(
            node_id=child_id,
            prompt=prompt,
            parent_id=parent_id,
            mutation_applied=mutation_applied,
            generation=generation,
            is_jailbroken=is_jailbroken,
            jailbreak_score=jailbreak_score,
            model_tested=model,
        )
        self._nodes[child_id] = node

        if parent:
            parent.children.append(child_id)

        return child_id

    def get_lineage(self, node_id: str) -> list[str]:
        """Return the ancestry chain from root seed to this node."""
        chain = []
        current = node_id
        while current is not None:
            chain.append(current)
            node = self._nodes.get(current)
            current = node.parent_id if node else None
        return list(reversed(chain))

    def get_root(self, node_id: str) -> Optional[str]:
        """Return the seed ancestor of a given node."""
        chain = self.get_lineage(node_id)
        return chain[0] if chain else None

    def analyze(self) -> GenealogyResult:
        """Run full genealogy analysis."""
        nodes = self._nodes

        if not nodes:
            return GenealogyResult(
                nodes={},
                successful_lineages=[],
                mutation_efficiency={},
                seed_productivity={},
                generational_fitness={},
                shortest_chain_length=None,
                avg_successful_chain_length=0.0,
                most_effective_mutation=None,
                most_productive_seed=None,
            )

        # Successful lineages: chains ending at a jailbroken node
        successful_lineages = []
        for node_id, node in nodes.items():
            if node.is_jailbroken:
                chain = self.get_lineage(node_id)
                successful_lineages.append(chain)

        # Sort by chain length (shortest first)
        successful_lineages.sort(key=len)

        # Chain length stats
        chain_lengths = [len(c) for c in successful_lineages]
        shortest = min(chain_lengths) if chain_lengths else None
        avg_length = sum(chain_lengths) / max(len(chain_lengths), 1)

        # Mutation Efficiency: jailbreak rate per mutation operator
        mutation_counts: dict[str, int] = {}
        mutation_successes: dict[str, int] = {}
        for node in nodes.values():
            if node.mutation_applied:
                mutation_counts[node.mutation_applied] = (
                    mutation_counts.get(node.mutation_applied, 0) + 1
                )
                if node.is_jailbroken:
                    mutation_successes[node.mutation_applied] = (
                        mutation_successes.get(node.mutation_applied, 0) + 1
                    )

        mutation_efficiency = {
            mut: mutation_successes.get(mut, 0) / count
            for mut, count in mutation_counts.items()
        }

        # Seed Productivity: weighted jailbreak yield per seed
        seed_nodes = {nid: n for nid, n in nodes.items() if n.generation == 0}
        seed_productivity: dict[str, float] = {}

        for seed_id in seed_nodes:
            # Count jailbreaks in subtree rooted at seed
            subtree_jb = 0
            subtree_total = 0
            for node in nodes.values():
                if self.get_root(node.node_id) == seed_id:
                    subtree_total += 1
                    if node.is_jailbroken:
                        subtree_jb += 1
            productivity = (subtree_jb / subtree_total) if subtree_total > 0 else 0.0
            seed_productivity[seed_id] = productivity

        # Generational Fitness: ASR per generation depth
        gen_counts: dict[int, int] = {}
        gen_successes: dict[int, int] = {}
        for node in nodes.values():
            g = node.generation
            gen_counts[g] = gen_counts.get(g, 0) + 1
            if node.is_jailbroken:
                gen_successes[g] = gen_successes.get(g, 0) + 1

        generational_fitness = {
            g: gen_successes.get(g, 0) / count
            for g, count in gen_counts.items()
        }

        most_effective_mutation = (
            max(mutation_efficiency, key=mutation_efficiency.get)
            if mutation_efficiency else None
        )
        most_productive_seed = (
            max(seed_productivity, key=seed_productivity.get)
            if seed_productivity else None
        )

        return GenealogyResult(
            nodes=nodes,
            successful_lineages=successful_lineages,
            mutation_efficiency=mutation_efficiency,
            seed_productivity=seed_productivity,
            generational_fitness=generational_fitness,
            shortest_chain_length=shortest,
            avg_successful_chain_length=avg_length,
            most_effective_mutation=most_effective_mutation,
            most_productive_seed=most_productive_seed,
        )


# ── Convenience: Build Tree from Generator Output ────────────────────────────

def build_tree_from_generator_output(
    seeds: list[str],
    mutations: list[dict],
    model: Optional[str] = None,
) -> GenealogyTree:
    """
    Build a GenealogyTree from the output of generators.expand_for_benchmark().

    Args:
        seeds: List of original seed prompt texts.
        mutations: List of dicts with keys:
            prompt, seed_index, mutation_type, is_jailbroken, score
        model: Model name tested (for attribution).

    Returns:
        Populated GenealogyTree ready for analysis.
    """
    tree = GenealogyTree()

    seed_ids: list[str] = []
    for i, seed_text in enumerate(seeds):
        sid = f"seed-{i}"
        tree.add_seed(sid, seed_text, model=model)
        seed_ids.append(sid)

    for j, m in enumerate(mutations):
        seed_idx = m.get("seed_index", 0)
        parent_id = seed_ids[seed_idx] if seed_idx < len(seed_ids) else seed_ids[0]
        tree.add_mutation(
            parent_id=parent_id,
            prompt=m["prompt"],
            mutation_applied=m.get("mutation_type", "unknown"),
            is_jailbroken=m.get("is_jailbroken", False),
            jailbreak_score=m.get("score", 0.0),
            model=model,
            child_id=f"mut-{j}",
        )

    return tree
