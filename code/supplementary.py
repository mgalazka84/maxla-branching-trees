"""Reproduce the permutation audit and the two-hub sharpness construction."""
from itertools import permutations
from pathlib import Path
import json
import networkx as nx
from maxla import solve, arrangement_value, bipartite_solution
from validate import load_oracle

ROOT = Path(__file__).resolve().parents[1]


def sharpness_tree(m):
    # a=0, c=1, b=2; A leaves first, then B leaves.
    a_leaves = list(range(3, 3 + m))
    b_leaves = list(range(3 + m, 3 + 2 * m))
    edges = [(0, 1), (1, 2)]
    edges += [(0, v) for v in a_leaves] + [(2, v) for v in b_leaves]
    order = [0] + b_leaves + [1] + a_leaves + [2]
    return 2 * m + 3, edges, order


def main():
    oracle = load_oracle()
    tree_count = permutation_count = 0
    for n in range(1, 8):
        graphs = [nx.empty_graph(1)] if n == 1 else nx.nonisomorphic_trees(n)
        for graph in graphs:
            edges = list(graph.edges())
            maximum = 0
            for order in permutations(range(n)):
                maximum = max(maximum, arrangement_value(edges, order))
                permutation_count += 1
            assert maximum == oracle(n, edges)
            tree_count += 1
    audit = dict(trees=tree_count, permutations=permutation_count,
                 max_n=7, mismatches=0)
    (ROOT / 'results/permutation_audit.json').write_text(json.dumps(audit, indent=2))
    rows = []
    for m in list(range(2, 31)) + [100, 1000]:
        n, edges, order = sharpness_tree(m)
        witness = arrangement_value(edges, order)
        bipartite = bipartite_solution(n, edges)['value']
        assert witness == 3*m*m + 5*m + 2
        assert bipartite == 2*m*m + 6*m + 3
        answer = solve(n, edges)
        assert answer['value'] >= witness
        if n <= 21:
            assert answer['value'] == oracle(n, edges)
        rows.append(dict(m=m, n=n, witness=witness, bipartite=bipartite,
                         algorithm_value=answer['value'],
                         witness_ratio=witness/bipartite))
    (ROOT / 'results/sharpness.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(dict(permutation_audit=audit, sharpness_cases=len(rows),
                         mismatches=0), indent=2))


if __name__ == '__main__':
    main()
