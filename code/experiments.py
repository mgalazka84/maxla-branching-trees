"""Component audits, targeted oracle checks, and controlled large-tree timings."""
from collections import Counter
from dataclasses import astuple
import json
from pathlib import Path
import platform
import random
import time
from maxla import (Profile, bridge_profiles, edge_signs, hub_options, solve,
                   arrangement_value, bipartite_solution)
from validate import load_oracle

ROOT = Path(__file__).resolve().parents[1]


def audits():
    bridge_checks = 0
    for length in range(1, 101):
        compressed = {astuple(p)[2:] for p in bridge_profiles(length)}
        for zero in [-1] + list(range(1, length)):
            for first in (-1, 1):
                signs = edge_signs(length, first, zero)
                levels = [signs[i] - signs[i-1] for i in range(1, length)]
                signature = (signs[0], -signs[-1],
                             levels[0] if levels else None,
                             levels[-1] if levels else None,
                             levels.count(2), levels.count(-2), levels.count(0))
                assert signature in compressed
                bridge_checks += 1
    hub_checks = 0
    for a1 in range(7):
        for ae in range(7-a1):
            for ao in range(7-a1-ae):
                for dc in range(7):
                    degree = a1 + ae + ao + dc
                    if degree < 3:
                        continue
                    for core in range(-dc, dc+1, 2):
                        actual = set()
                        for d in range(a1+1):
                            for e in range(ae+1):
                                for o in range(ao+1):
                                    p = d+e+o
                                    h = core + 2*p - a1-ae-ao
                                    valid = ((d == 0 or h > -1)
                                             and (d == a1 or h < 1)
                                             and (e+o == 0 or h > -2)
                                             and (e+o == ae+ao or h < 2))
                                    if valid:
                                        actual.add((h,p,e))
                        predicted = set()
                        for h,p,lo,hi,dl,du in hub_options(a1,ae,ao,core,degree):
                            predicted.update((h,p,e) for e in range(lo,hi+1))
                        assert actual == predicted, (a1,ae,ao,dc,core,actual,predicted)
                        hub_checks += 1
    return dict(bridge_profile_patterns=bridge_checks,
                hub_count_configurations=hub_checks, mismatches=0)


def structured_tree(b, seed, length_max=3, extra_arms=0, core_length=None):
    rng = random.Random(seed)
    skeleton = [(i, rng.randrange(i)) for i in range(1,b)]
    degrees = Counter(v for edge in skeleton for v in edge)
    edges = []
    next_vertex = b
    def add_path(u,v,length):
        nonlocal next_vertex
        path=[u]
        for _ in range(length-1):
            path.append(next_vertex)
            next_vertex += 1
        if v is None:
            v=next_vertex
            next_vertex+=1
        path.append(v)
        edges.extend(zip(path,path[1:]))
    for u,v in skeleton:
        add_path(u,v,core_length or rng.randint(1,length_max))
    for u in range(b):
        for _ in range(max(0,3-degrees[u])+extra_arms):
            add_path(u,None,rng.randint(1,length_max))
    return next_vertex,edges


def main():
    output = ROOT / 'results'
    audit = audits()
    print('AUDIT',audit,flush=True)
    oracle=load_oracle()
    targeted=[]
    for b in (3,4):
        accepted=0
        for seed in range(10000):
            n,edges=structured_tree(b, seed, length_max=2)
            if n>21:
                continue
            answer=solve(n,edges)
            exact=oracle(n,edges)
            assert answer['value']==exact
            targeted.append(dict(b=b,seed=seed,n=n,optimum=exact))
            accepted+=1
            if accepted==100:
                break
    print('TARGETED',len(targeted),flush=True)
    # Check invariance under relabeling on a wider, bounded-order sample.
    rng=random.Random(20261018)
    relabel_checks=0
    for b in (3,4):
        for seed in range(10):
            n,edges=structured_tree(b, seed+11000,length_max=4)
            answer=solve(n,edges)
            labels=list(range(n)); rng.shuffle(labels)
            changed=[(labels[u],labels[v]) for u,v in edges]
            assert solve(n,changed)['value']==answer['value']
            relabel_checks+=1
    timings=[]
    for b in (1,2,3,4):
        for extra in (0,10,100,1000):
            n,edges=structured_tree(b,20261018,length_max=5,extra_arms=extra,
                                    core_length=7)
            start=time.perf_counter()
            answer=solve(n,edges)
            duration=time.perf_counter()-start
            assert arrangement_value(edges,answer['order'])==answer['value']
            row=dict(b=b,extra_arms_per_hub=extra,n=n,
                     seconds=round(duration,6),optimum=answer['value'],
                     bipartite=bipartite_solution(n,edges)['value'],
                     bridge_assignments=answer['bridge_assignments'],
                     hub_assignments=answer['hub_assignments'])
            timings.append(row)
            print('TIMING',json.dumps(row),flush=True)
    result=dict(audits=audit,targeted_oracle_cases=targeted,
                relabeling_checks=relabel_checks,benchmarks=timings,
                python=platform.python_version(),platform=platform.platform(),
                seed=20261018)
    (output/'experiments.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
