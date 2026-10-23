# Maximum linear arrangement of trees with few branching vertices

An exact solver for a simple question: how should the vertices of a tree be
placed in a row so that the **sum of distances between connected vertices is
as large as possible**?

The solver is parameterized by the number `b` of branching vertices (vertices
of degree at least three). Its time bound is `O(n + 32^b b log(b+2))` for `b >= 1`,
with a linear-time path case. Degrees and path lengths may be arbitrarily
large. The dependence on `b` is exponential; this is not a polynomial-time
solver for unrestricted trees. Edges must have unit weight.

## Quick start

The solver needs Python 3.10 or later and uses only the standard library.
Run from the repository root:

```sh
python code/maxla.py results/example_b4.json
python code/maxla.py results/example_b4.json --oracle
```

The example has 13 vertices and four branching vertices. The returned optimum
is **92**, whereas the best bipartite arrangement has value **87**. The JSON
output contains `value` and `order`; `order` lists vertex IDs from left to right.
The optional subset oracle is exponential and is intended for small inputs.

For another instance, save a JSON file with `n` and an edge list:

```json
{"n": 4, "edges": [[0, 1], [0, 2], [0, 3]]}
```

Vertex IDs must be the integers `0, ..., n-1`. The input must be a nonempty,
connected, simple tree. Numbering positions from zero or from one gives the
same edge lengths.

## Reproduce the verification

The verification environment uses Python 3.12 or later, NetworkX 3.7, and a
C++17 compiler. NetworkX is used to enumerate nonisomorphic trees; the solver
does not depend on it. The commands below were checked on Linux with `g++`.

```sh
python -m pip install -r requirements-verification.txt
g++ -O3 -std=c++17 -shared -fPIC code/oracle.cpp -o code/oracle.so
python code/validate.py --max-n 15 --output results
python code/experiments.py
python code/supplementary.py
python code/extended_experiments.py
```

The C++ oracle uses a subset dynamic program over cut sizes, independently of
the solver's path profiles and level states. It supports at most 24 vertices
and uses exponential memory. Run Python without `-O` so that verification
assertions remain enabled.

Expected checks:

| Check | Recorded result |
|---|---:|
| Nonisomorphic trees with at most 15 vertices | 13,188; zero mismatches |
| Trees with three / four branching vertices | 5,441 / 3,634 |
| Optimum strictly above the bipartite value | 1,546 trees |
| Targeted oracle comparisons with three/four hubs | 200 |
| Additional oracle comparisons with five/six hubs, orders 20/22/24 | 60; zero mismatches |
| Exhaustive checks of the specialized two-hub baseline | 3,287 |
| Relabeling checks | 20 |
| Bridge orientation patterns | 10,100 |
| Hub-count configurations | 2,331 |
| Direct permutation audit | 25 trees; 60,177 permutations |
| Two-hub family formula checks | 31 |

`validate.py` accepts a separate output directory with `--output`. The commands
above overwrite the recorded files in `results/`; use a separate working copy
to preserve original timings. `extended_experiments.py` reads `results/exhaustive.csv`
and then records its own results. Its time-limit runs stop at the first timeout
in each family, with an upper cap of 20 hubs.
The recorded targeted cases have at most 18 vertices, although the generator
accepts instances up to 21.

## Files

| Path | Purpose |
|---|---|
| `code/maxla.py` | Exact solver, reconstruction, bipartite baseline, Python oracle |
| `code/oracle.cpp` | Independent C++ subset oracle |
| `code/baseline_two_hubs.py` | Specialized linear-time baseline for at most two hubs |
| `code/extended_experiments.py` | Repeated timings, strict-gap families, larger oracle cases, practical limits and gap statistics |
| `code/validate.py` | Exhaustive comparison on nonisomorphic trees |
| `code/experiments.py` | Component audits, targeted cases, relabeling, timings |
| `code/supplementary.py` | Direct permutation audit and two-hub family checks |
| `results/exhaustive.csv` | One row for each of the 13,188 trees, including feasible-state and histogram counts |
| `results/extended.json` | Expanded experiments, all larger sampled edge lists, seeds, timings and counters |
| `results/gap_summary.csv` | Maximum ratio and number of extremizers at each order |
| `results/gap_extremizers.json` | Edge lists and graph6 for all ratio-maximizing trees of orders 2–15 |
| `results/exhaustive_summary.json` | Counts and timings by tree order |
| `results/experiments.json` | Seeds, targeted cases, audits, environment, benchmarks |
| `results/example_b4.json` | Explicit example with optimum 92 and bipartite value 87 |
| `results/permutation_audit.json` | Independent check of the subset oracle |
| `results/sharpness.json` | Values for the explicit two-hub family |
| `results/nonbipartite_examples.json` | Further examples with strict gaps |

## Algorithm and benchmark details

Each bridge has at most **eight** profiles. Telescoping internal levels shows
that all strictly interior zero positions have the same endpoint data and
histogram, regardless of parity. There are at most four states per odd-degree
hub and three per even-degree hub. A single concave integer variable handles
all residual antenna choices. Histogram evaluation uses sorted prefix sums.

`baseline_two_hubs.py` independently implements the characterization in
Alemany-Puig, Esteban and Ferrer-i-Cancho (2026), Section 5.2, Algorithms 4.1/5.2
and Theorem 5.4: [DOI 10.1007/s10878-026-01454-z](https://doi.org/10.1007/s10878-026-01454-z).
It does not call the profile solver and is not the authors' Linear Arrangement
Library implementation. It uses alternating component signs and bucket ordering.

Recorded experiments were run on **23 October 2026**, with Python 3.12.14,
NetworkX 3.7 and GCC 13.3.0, on a shared Linux x86-64 AMD EPYC 9V74 host.
`extended.json` reports five-run median/minimum/maximum times for the controlled
sizes, three-run summaries for strict-gap families, and single-run 15-second
limits. The original `experiments.json` contains single-run observations.
Large instances are checked by evaluating the returned permutation; only
instances of order at most 24 are sent to the exponential oracle.

The expanded strict-gap families are:

- `T_m`: a length-two hub-to-hub path and `m` pendant leaves at each hub;
  `OPT = 3m² + 5m + 2`, `BIP = 2m² + 6m + 3` for `m >= 2`.
- `R_m`: a central hub connected through three length-two paths to peripheral
  hubs with `m` leaves each; this includes the 92/87 example at `m = 2`.

Both were tested at `m = 2, 3, 5, 10, 30, 100, 1000`. The `R_m` values are
computational results, without a claimed closed formula. The 60 larger random
oracle cases contain eight strict gaps. Across the exhaustive set, the largest
ratio is `140/111` at order 15. Every extremizer is explicitly serialized.

There is no universal practical hub limit. In the recorded family with
length-seven core paths, six hubs finished in about 8.58 seconds and seven
exceeded 15 seconds. With direct core edges, 13 hubs finished in about 13.68
seconds and 14 timed out. These limits depend on the specified family and host.

Output counters distinguish bridge assignments, generated hub assignments,
feasible assignments after boundary checks, and actual histogram evaluations.
Repeated scalar values within one state are cached. The implementation uses
parity, local antenna intervals and boundary filtering, with no hidden
branch-and-bound pruning. Run without Python `-O` to keep all assertions active.

## Version and license

Version **1.1.0** contains the eight-profile solver, the specialized baseline,
and the expanded verification data. Version 1.0.0 remains available as an earlier release.
See `CITATION.cff` for software citation metadata. The repository is distributed
under the MIT license; see `LICENSE`.
