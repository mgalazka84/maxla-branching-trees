"""Version 1.1 experiments: baselines, strict gaps, larger oracles and limits."""
from collections import Counter
import csv
from fractions import Fraction
import json
import multiprocessing as mp
from pathlib import Path
import platform
import random
import statistics
import subprocess
import time
import networkx as nx
from maxla import solve, bipartite_solution, arrangement_value
from baseline_two_hubs import solve_two_hubs
from experiments import structured_tree
from validate import load_oracle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'
COUNTERS = ('bridge_assignments', 'hub_assignments',
            'feasible_assignments', 'histogram_evaluations')


def measure(function, n, edges, repeats=5):
    seconds = []
    for _ in range(repeats):
        start = time.perf_counter()
        answer = function(n, edges)
        seconds.append(time.perf_counter() - start)
        assert arrangement_value(edges, answer['order']) == answer['value']
    return dict(value=answer['value'], median_seconds=statistics.median(seconds),
                min_seconds=min(seconds), max_seconds=max(seconds), repeats=repeats,
                **{key: answer[key] for key in COUNTERS if key in answer})


def gap_tree(m, four=False):
    if not four:
        edges = [(0, 2), (2, 1)]
        next_v = 3
        hubs = (0, 1)
    else:
        edges = [(0, 4), (4, 1), (0, 5), (5, 2), (0, 6), (6, 3)]
        next_v = 7
        hubs = (1, 2, 3)
    for h in hubs:
        for _ in range(m):
            edges.append((h, next_v))
            next_v += 1
    return next_v, edges


def target_tree(b, n, seed):
    rng = random.Random(seed)
    edges = [(v, rng.randrange(v)) for v in range(1, b)]
    degree = Counter(v for edge in edges for v in edge)
    next_v = b
    for h in range(b):
        for _ in range(max(0, 3-degree[h])):
            edges.append((h, next_v))
            next_v += 1
    while next_v < n:
        if rng.random() < .8:
            index = rng.randrange(len(edges))
            u, v = edges.pop(index)
            edges.extend(((u, next_v), (next_v, v)))
        else:
            edges.append((rng.randrange(b), next_v))
        next_v += 1
    assert next_v == n
    assert sum(d >= 3 for d in Counter(v for e in edges for v in e).values()) == b
    return edges


def limit_worker(queue, n, edges):
    start = time.perf_counter()
    answer = solve(n, edges)
    assert arrangement_value(edges, answer['order']) == answer['value']
    queue.put(dict(seconds=time.perf_counter()-start, optimum=answer['value'],
                   **{key:answer[key] for key in COUNTERS}))


def gap_statistics():
    with (OUT/'exhaustive.csv').open() as stream:
        rows = [{k:int(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    positive = [row for row in rows if row['gap'] > 0]
    ratios = sorted(Fraction(row['optimum'], row['bipartite']) for row in positive)
    summaries, extrema = [], []
    bounds = [Fraction(1), Fraction(41,40), Fraction(21,20), Fraction(43,40),
              Fraction(11,10), Fraction(9,8), Fraction(23,20), Fraction(3,2)]
    bins = [dict(lower_exclusive=str(a), upper_inclusive=str(b),
                 count=sum(a < x <= b for x in ratios)) for a,b in zip(bounds,bounds[1:])]
    for n in range(2, 16):
        subset = [row for row in rows if row['n'] == n]
        highest = max(Fraction(row['optimum'], row['bipartite']) for row in subset)
        winners = [row for row in subset if Fraction(row['optimum'], row['bipartite']) == highest]
        summaries.append(dict(n=n, trees=len(subset), positive=sum(r['gap']>0 for r in subset),
                              max_ratio=str(highest), max_ratio_decimal=float(highest),
                              maximizers=len(winners)))
        indices = {row['index']:row for row in winners}
        for index, graph in enumerate(nx.nonisomorphic_trees(n)):
            if index in indices:
                extrema.append(dict(**indices[index], ratio=str(highest),
                    graph6=nx.to_graph6_bytes(graph,header=False).decode().strip(),
                    edges=list(graph.edges())))
    with (OUT/'gap_summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summaries[0]))
        writer.writeheader(); writer.writerows(summaries)
    (OUT/'gap_extremizers.json').write_text(json.dumps(extrema,indent=2)+'\n')
    return dict(positive_trees=len(positive), minimum=str(ratios[0]),
        median=float(statistics.median(ratios)), maximum=str(ratios[-1]),
        percentile90_nearest_rank=float(ratios[(9*len(ratios)+9)//10-1]),
        bins=bins, by_order=summaries, all_maximizers='gap_extremizers.json')


def main():
    cpu = next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                if line.startswith('model name')), 'unknown')
    result = dict(date='2026-10-23', python=platform.python_version(),
        networkx=nx.__version__, platform=platform.platform(), cpu=cpu,
        compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
        compile_flags='-std=c++17 -O3 -shared -fPIC', seed=20261023,
        hardware_note='Shared virtual host; single-process wall times, no dedicated CPU reservation.',
        controlled=[], strict_gap=[], targeted=[], practical_limits=[], gap_statistics=gap_statistics())
    def save():
        (OUT/'extended.json').write_text(json.dumps(result,indent=2)+'\n')
    for b in (1,2,3,4):
        for extra in (0,10,100,1000):
            n, edges = structured_tree(b,20261018,length_max=5,extra_arms=extra,core_length=7)
            row=dict(b=b,n=n,extra_arms_per_hub=extra,solver=measure(solve,n,edges))
            if b <= 2:
                row['baseline_aef']=measure(solve_two_hubs,n,edges)
                assert row['solver']['value']==row['baseline_aef']['value']
            result['controlled'].append(row)
            print('CONTROLLED',b,n,round(row['solver']['median_seconds'],6),flush=True)
            save()
    oracle=load_oracle()
    for four in (False,True):
        for m in (2,3,5,10,30,100,1000):
            n,edges=gap_tree(m,four)
            run=measure(solve,n,edges,repeats=3)
            bip=bipartite_solution(n,edges)['value']
            assert run['value']>bip
            if not four:
                assert run['value']==3*m*m+5*m+2 and bip==2*m*m+6*m+3
            exact=oracle(n,edges) if n<=24 else None
            assert exact is None or exact==run['value']
            result['strict_gap'].append(dict(family='R' if four else 'T',m=m,n=n,
                bipartite=bip,oracle=exact,solver=run))
            save()
    for b in (5,6):
        for n in (20,22,24):
            for sample in range(10):
                seed=20261023+10000*b+100*n+sample
                edges=target_tree(b,n,seed)
                start=time.perf_counter(); answer=solve(n,edges)
                seconds=time.perf_counter()-start
                start=time.perf_counter(); exact=oracle(n,edges)
                oracle_seconds=time.perf_counter()-start
                assert answer['value']==exact
                assert arrangement_value(edges,answer['order'])==exact
                result['targeted'].append(dict(b=b,n=n,seed=seed,edges=edges,optimum=exact,
                    bipartite=bipartite_solution(n,edges)['value'],seconds=seconds,
                    oracle_seconds=oracle_seconds,**{key:answer[key] for key in COUNTERS}))
                save()
            print('TARGET',b,n,'10 cases passed',flush=True)
    timeout=15
    result['timeout_seconds']=timeout
    context=mp.get_context('spawn')
    for length in (1,7):
        for b in range(4,21):
            n,edges=structured_tree(b,20261018,length_max=3,extra_arms=0,core_length=length)
            queue=context.Queue(); process=context.Process(target=limit_worker,args=(queue,n,edges))
            start=time.perf_counter(); process.start(); process.join(timeout)
            row=dict(b=b,n=n,core_length=length,timeout_seconds=timeout)
            if process.is_alive():
                process.terminate(); process.join()
                row['status']='timeout'
            else:
                if process.exitcode != 0: raise RuntimeError('Limit worker failed')
                row.update(queue.get(timeout=2)); row['status']='completed'
            row['parent_elapsed_seconds']=time.perf_counter()-start
            result['practical_limits'].append(row); save()
            print('LIMIT',json.dumps(row),flush=True)
            queue.close()
            if row['status']=='timeout': break
    result['mismatches']=0
    save()
    print('EXTENDED COMPLETE',len(result['targeted']),'larger oracle cases',flush=True)


if __name__=='__main__':
    main()
