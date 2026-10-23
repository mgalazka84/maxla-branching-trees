"""Linear-time reference for at most two hubs, based on AEF (2026), Section 5.2.

DOI: 10.1007/s10878-026-01454-z, Algorithms 4.1 and 5.2 / Theorem 5.4.
This is an independent Python implementation of the characterization, not a
binding to the authors' Linear Arrangement Library. It uses no path profiles,
hub-state enumeration, or concave optimization.
"""
from maxla import adjacency, arrangement_value


def level_order(levels):
    n=len(levels)
    buckets=[[] for _ in range(2*n+1)]
    for v,h in enumerate(levels):
        buckets[h+n].append(v)
    return [v for bucket in reversed(buckets) for v in bucket]


def solve_two_hubs(n,edges):
    adj=adjacency(n,edges)
    hubs=[v for v in range(n) if len(adj[v])>=3]
    if len(hubs)>2:
        raise ValueError('Reference algorithm supports at most two hubs')
    signs=[0]*n; signs[0]=1; stack=[0]
    while stack:
        v=stack.pop()
        for w in adj[v]:
            if not signs[w]: signs[w]=-signs[v]; stack.append(w)
    order=level_order([signs[v]*len(adj[v]) for v in range(n)])
    best={'value':arrangement_value(edges,order),'order':order}
    if len(hubs)<2: return best
    parent={hubs[0]:None}; stack=[hubs[0]]
    while stack:
        v=stack.pop()
        if v==hubs[1]: break
        for w in adj[v]:
            if w not in parent: parent[w]=v; stack.append(w)
    path=[hubs[1]]
    while path[-1]!=hubs[0]: path.append(parent[path[-1]])
    if len(path)==2: return best
    t=path[1]  # An arbitrary internal vertex of the hub-to-hub path.
    u,v=adj[t]
    signs=[0]*n; signs[u]=1; signs[v]=-1; stack=[u,v]
    while stack:
        x=stack.pop()
        for y in adj[x]:
            if y!=t and not signs[y]: signs[y]=-signs[x]; stack.append(y)
    levels=[signs[x]*len(adj[x]) for x in range(n)]
    assert levels[t]==0 and sum(levels)==0
    order=level_order(levels)
    value=arrangement_value(edges,order)
    if value>best['value']: best={'value':value,'order':order}
    return best
