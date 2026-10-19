"""Exhaustive unlabelled-tree comparison against an independent subset oracle.

Dependency: networkx (for nonisomorphic tree generation only).
Compile oracle.cpp as described in README.md; the solver itself is pure Python.
"""
import argparse
import csv
import ctypes
import json
from pathlib import Path
import time
import networkx as nx
from maxla import solve, bipartite_solution, arrangement_value

HERE = Path(__file__).resolve().parent


def load_oracle():
    lib = ctypes.CDLL(str(HERE / "oracle.so"))
    lib.maxla_oracle.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lib.maxla_oracle.restype = ctypes.c_longlong
    def oracle(n, edges):
        array = (ctypes.c_int * (2 * len(edges)))(*[x for e in edges for x in e])
        return lib.maxla_oracle(n, array)
    return oracle


def run(max_n, destination):
    destination.mkdir(parents=True, exist_ok=True)
    oracle = load_oracle()
    records = []
    summaries = []
    examples = []
    for n in range(1, max_n + 1):
        trees = [nx.empty_graph(1)] if n == 1 else nx.nonisomorphic_trees(n)
        count = nonbip = 0
        elapsed_solver = elapsed_oracle = 0
        max_b = 0
        for index, graph in enumerate(trees):
            edges = list(graph.edges())
            start = time.perf_counter()
            answer = solve(n, edges)
            assert sorted(answer['order']) == list(range(n))
            assert arrangement_value(edges, answer['order']) == answer['value']
            elapsed_solver += time.perf_counter() - start
            start = time.perf_counter()
            exact = oracle(n, edges)
            elapsed_oracle += time.perf_counter() - start
            if answer['value'] != exact:
                failure = dict(n=n, edges=edges, answer=answer, exact=exact)
                (destination / 'FAILURE.json').write_text(json.dumps(failure, indent=2))
                raise AssertionError(failure)
            baseline = bipartite_solution(n, edges)['value']
            gap = exact - baseline
            if gap and len(examples) < 30:
                examples.append(dict(n=n, edges=edges, exact=exact,
                                     bipartite=baseline, **answer))
            count += 1
            nonbip += gap > 0
            max_b = max(max_b, answer['hubs'])
            records.append(dict(n=n, index=index, hubs=answer['hubs'],
                                optimum=exact, bipartite=baseline, gap=gap,
                                bridge_assignments=answer['bridge_assignments'],
                                hub_assignments=answer['hub_assignments'],
                                feasible_assignments=answer['feasible_assignments']))
        row = dict(n=n, trees=count, max_hubs=max_b, nonbipartite_optimum=nonbip,
                   mismatches=0, solver_seconds=round(elapsed_solver,6),
                   oracle_seconds=round(elapsed_oracle,6))
        summaries.append(row)
        print(json.dumps(row), flush=True)
        (destination / 'exhaustive_summary.json').write_text(json.dumps(summaries, indent=2))
    with (destination / 'exhaustive.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (destination / 'nonbipartite_examples.json').write_text(json.dumps(examples, indent=2))
    print('TOTAL', sum(x['trees'] for x in summaries), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-n', type=int, default=14)
    p.add_argument('--output', type=Path, default=HERE.parent / 'results')
    a = p.parse_args()
    run(a.max_n, a.output)
