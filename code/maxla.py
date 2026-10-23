"""Exact maximum linear arrangement of unweighted trees, parameterized by hubs.

Reference implementation, version 1.1.0. Standard library only.
Hubs are vertices of degree at least three. Input trees are unweighted.
"""
from collections import Counter
from dataclasses import dataclass
from itertools import product
import argparse
import json


def adjacency(n, edges):
    if n < 1 or len(edges) != n - 1:
        raise ValueError("Expected a nonempty tree")
    adj = [[] for _ in range(n)]
    seen = set()
    for u, v in edges:
        if not (0 <= u < n and 0 <= v < n) or u == v:
            raise ValueError("Invalid edge")
        edge = tuple(sorted((u, v)))
        if edge in seen:
            raise ValueError("Duplicate edge")
        seen.add(edge)
        adj[u].append(v)
        adj[v].append(u)
    visited = {0}
    stack = [0]
    while stack:
        for v in adj[stack.pop()]:
            if v not in visited:
                visited.add(v)
                stack.append(v)
    if len(visited) != n:
        raise ValueError("Disconnected input")
    return adj


def arrangement_value(edges, order):
    pos = {v: i for i, v in enumerate(order)}
    return sum(abs(pos[u] - pos[v]) for u, v in edges)


def histogram_value(hist):
    """Half the sum of pairwise absolute level differences, using integers."""
    count = level_sum = twice_value = 0
    for level, multiplicity in sorted(hist.items()):
        if multiplicity < 0:
            raise AssertionError("Negative histogram count")
        twice_value += multiplicity * (level * count - level_sum)
        count += multiplicity
        level_sum += level * multiplicity
    if level_sum or twice_value % 2:
        raise AssertionError("Not a zero-sum integral level histogram")
    return twice_value // 2


def bipartite_solution(n, edges):
    adj = adjacency(n, edges)
    color = [-1] * n
    color[0] = 0
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if color[v] == -1:
                color[v] = color[u] ^ 1
                stack.append(v)
    buckets = [{}, {}]
    for v in range(n):
        buckets[color[v]].setdefault(len(adj[v]), []).append(v)
    order = [v for d in sorted(buckets[0], reverse=True) for v in buckets[0][d]]
    order += [v for d in sorted(buckets[1]) for v in buckets[1][d]]
    return {"value": arrangement_value(edges, order), "order": order}


@dataclass(frozen=True)
class Profile:
    first_sign: int
    zero: int  # internal index 1..L-1, or -1
    left: int
    right: int
    first_level: int | None
    last_level: int | None
    plus2: int
    minus2: int
    zeros: int


def edge_signs(length, first, zero=-1):
    signs = [first]
    for i in range(1, length):
        signs.append(signs[-1] if i == zero else -signs[-1])
    return signs


def bridge_profiles(length):
    positions = {-1}
    if length >= 2:
        positions.update((1, length - 1))
        # Every interior zero has the same boundary levels and histogram.
        # Telescoping fixes the signed difference of the +2 and -2 counts.
        if length >= 4:
            positions.add(2)
    out = []
    for zero in sorted(positions):
        for first in (-1, 1):
            signs = edge_signs(length, first, zero)
            levels = [signs[i] - signs[i - 1] for i in range(1, length)]
            out.append(Profile(first, zero, signs[0], -signs[-1],
                               levels[0] if levels else None,
                               levels[-1] if levels else None,
                               levels.count(2), levels.count(-2), levels.count(0)))
    assert len(out) <= 8
    return out


def decompose(adj):
    hubs = [u for u in range(len(adj)) if len(adj[u]) >= 3]
    index = {u: i for i, u in enumerate(hubs)}
    antennas = [[] for _ in hubs]
    bridges = []
    for h in hubs:
        for v in adj[h]:
            path = [h, v]
            prev, cur = h, v
            while len(adj[cur]) == 2:
                nxt = adj[cur][0] if adj[cur][0] != prev else adj[cur][1]
                path.append(nxt)
                prev, cur = cur, nxt
            if len(adj[cur]) == 1:
                antennas[index[h]].append(path)
            elif h < cur:
                bridges.append((index[h], index[cur], path))
    assert not hubs or len(bridges) == len(hubs) - 1
    return hubs, antennas, bridges


def hub_options(a1, ae, ao, core_sum, degree):
    """(level, number of positive antenna incidences, even-positive lo/hi,
    direct-positive lo/hi). At most four states, including parity filtering."""
    a = a1 + ae + ao
    candidates = []
    if a + core_sum >= 2:
        candidates.append(a + core_sum)
    if -a + core_sum <= -2:
        candidates.append(-a + core_sum)
    candidates.extend(h for h in (-1, 0, 1) if (degree - h) % 2 == 0)
    result = []
    for h in candidates:
        twice_p = a + h - core_sum
        if twice_p % 2:
            continue
        p = twice_p // 2
        if not 0 <= p <= a:
            continue
        if h >= 2:
            bounds = ((a1, a1), (ae, ae), (ao, ao))
        elif h <= -2:
            bounds = ((0, 0), (0, 0), (0, 0))
        else:
            direct = (a1, a1) if h == 1 else ((0, 0) if h == -1 else (0, a1))
            bounds = (direct, (0, ae), (0, ao))
        (dl, du), (el, eu), (ol, ou) = bounds
        lo = max(el, p - du - ou)
        hi = min(eu, p - dl - ol)
        if lo <= hi:
            result.append((h, p, lo, hi, dl, du))
    assert len(result) <= 4
    return result


def solve(n, edges, reconstruct=True):
    adj = adjacency(n, edges)
    hubs, antennas, bridges = decompose(adj)
    b = len(hubs)
    baseline = bipartite_solution(n, edges)
    if b == 0:
        return {**baseline, "hubs": 0, "bridge_assignments": 0,
                "hub_assignments": 0, "feasible_assignments": 0,
                "histogram_evaluations": 0}
    categories = []
    balanced = even_count = odd_count = 0
    for paths in antennas:
        cat = [[], [], []]  # direct, even-length, odd-length >=3
        for path in paths:
            length = len(path) - 1
            k = 0 if length == 1 else (1 if length % 2 == 0 else 2)
            cat[k].append(path)
            balanced += (length - 1) // 2
            even_count += length % 2 == 0
            odd_count += length % 2 == 1
        categories.append(cat)
    profiles = [bridge_profiles(len(path) - 1) for _, _, path in bridges]
    best = baseline["value"]
    best_data = None
    bridge_assignments = hub_assignments = feasible_assignments = histogram_evaluations = 0
    for chosen in product(*profiles):
        bridge_assignments += 1
        core_sums = [0] * b
        cp = cm = cz = 0
        for (i, j, path), profile in zip(bridges, chosen):
            core_sums[i] += profile.left
            core_sums[j] += profile.right
            cp += profile.plus2
            cm += profile.minus2
            cz += profile.zeros
        options = []
        for i, cat in enumerate(categories):
            options.append(hub_options(*(len(x) for x in cat), core_sums[i],
                                       len(adj[hubs[i]])))
        for states in product(*options):
            hub_assignments += 1
            levels = [s[0] for s in states]
            valid = True
            for (i, j, path), profile in zip(bridges, chosen):
                if len(path) == 2:
                    if profile.left * (levels[i] - levels[j]) <= 0:
                        valid = False
                        break
                elif (profile.left * (levels[i] - profile.first_level) <= 0
                      or profile.right * (levels[j] - profile.last_level) <= 0):
                    valid = False
                    break
            if not valid:
                continue
            feasible_assignments += 1
            lo = sum(s[2] for s in states)
            hi = sum(s[3] for s in states)
            p_total = sum(s[1] for s in states)
            value_cache = {}

            def value(e):
                nonlocal histogram_evaluations
                if e in value_cache:
                    return value_cache[e]
                histogram_evaluations += 1
                hist = Counter(levels)
                hist[2] += cp + balanced + even_count - e
                hist[-2] += cm + balanced + e
                hist[0] += cz
                leaf_plus = odd_count - p_total + 2 * e
                hist[1] += leaf_plus
                hist[-1] += odd_count + even_count - leaf_plus
                value_cache[e] = histogram_value(hist)
                return value_cache[e]

            candidate_es = {lo, hi}
            f_lo = value(lo)
            if lo < hi:
                delta = value(lo + 1) - f_lo
                q = (delta + 2) // 4
                candidate_es.update(max(lo, min(hi, lo + q + offset))
                                    for offset in (0, 1))
            for e in candidate_es:
                objective = value(e)
                if objective > best:
                    best = objective
                    best_data = (chosen, states, e)
    result = {"value": best, "hubs": b,
              "bridge_assignments": bridge_assignments,
              "hub_assignments": hub_assignments,
              "feasible_assignments": feasible_assignments,
              "histogram_evaluations": histogram_evaluations}
    if not reconstruct:
        return result
    if best_data is None:
        result["order"] = baseline["order"]
        return result
    chosen, states, e = best_data
    even_positives = [s[2] for s in states]
    left = e - sum(even_positives)
    for i, s in enumerate(states):
        take = min(left, s[3] - s[2])
        even_positives[i] += take
        left -= take
    assert left == 0
    directed = []

    def add_path(path, first, zero=-1):
        for (u, v), sign in zip(zip(path, path[1:]),
                                edge_signs(len(path) - 1, first, zero)):
            directed.append((u, v) if sign == 1 else (v, u))

    for (_, _, path), profile in zip(bridges, chosen):
        add_path(path, profile.first_sign, profile.zero)
    for i, (cat, state) in enumerate(zip(categories, states)):
        h, p, lo, hi, dl, du = state
        even = even_positives[i]
        odd = p - even
        direct = max(dl, odd - len(cat[2]))
        assert direct <= min(du, odd)
        for paths, count in zip(cat, (direct, even, odd - direct)):
            for k, path in enumerate(paths):
                add_path(path, 1 if k < count else -1)
    actual = [0] * n
    for u, v in directed:
        actual[u] += 1
        actual[v] -= 1
    assert len(directed) == n - 1
    assert all(actual[u] > actual[v] for u, v in directed)
    buckets = {}
    for u, level in enumerate(actual):
        buckets.setdefault(level, []).append(u)
    order = [u for level in sorted(buckets, reverse=True) for u in buckets[level]]
    assert arrangement_value(edges, order) == best
    result["order"] = order
    result["levels"] = actual
    return result


def subset_dp(n, edges):
    """Independent O(n 2^n) exact oracle, no path or orientation assumptions."""
    adj = adjacency(n, edges)
    masks = [sum(1 << v for v in neighbors) for neighbors in adj]
    size = 1 << n
    cut = [0] * size
    dp = [0] * size
    for mask in range(1, size):
        bit = mask & -mask
        v = bit.bit_length() - 1
        prev = mask ^ bit
        cut[mask] = cut[prev] + len(adj[v]) - 2 * (masks[v] & prev).bit_count()
        candidates = mask
        best = -1
        while candidates:
            bit = candidates & -candidates
            best = max(best, dp[mask ^ bit])
            candidates ^= bit
        dp[mask] = best + cut[mask]
    return dp[-1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON with n and zero-based edges")
    parser.add_argument("--oracle", action="store_true")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as stream:
        instance = json.load(stream)
    answer = solve(instance["n"], instance["edges"])
    if args.oracle:
        answer["oracle"] = subset_dp(instance["n"], instance["edges"])
        assert answer["value"] == answer["oracle"]
    print(json.dumps(answer, indent=2))
