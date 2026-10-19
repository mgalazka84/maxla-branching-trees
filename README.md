# Maximum linear arrangement of trees with few branching vertices

An exact solver for a simple question: how should the vertices of a tree be
placed in a row so that the **sum of distances between connected vertices is
as large as possible**?

The solver is parameterized by the number `b` of branching vertices (vertices
of degree at least three). Its time bound is `O(n + 40^b b^2)` for `b >= 1`,
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
python code/validate.py --max-n 15 --output reproduced/exhaustive
python code/experiments.py
python code/supplementary.py
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
| Targeted oracle comparisons | 200 |
| Relabeling checks | 20 |
| Bridge orientation patterns | 10,100 |
| Hub-count configurations | 2,331 |
| Direct permutation audit | 25 trees; 60,177 permutations |
| Two-hub family formula checks | 31 |

`validate.py` accepts a separate output directory, as shown above.
`experiments.py` and `supplementary.py` overwrite their corresponding files in
`results/`; use a separate working copy to preserve the recorded timings.
The recorded targeted cases have at most 18 vertices, although the generator
accepts instances up to 21.

## Files

| Path | Purpose |
|---|---|
| `code/maxla.py` | Exact solver, reconstruction, bipartite baseline, Python oracle |
| `code/oracle.cpp` | Independent C++ subset oracle |
| `code/validate.py` | Exhaustive comparison on nonisomorphic trees |
| `code/experiments.py` | Component audits, targeted cases, relabeling, timings |
| `code/supplementary.py` | Direct permutation audit and two-hub family checks |
| `results/exhaustive.csv` | One row for each of the 13,188 trees |
| `results/exhaustive_summary.json` | Counts and timings by tree order |
| `results/experiments.json` | Seeds, targeted cases, audits, environment, benchmarks |
| `results/example_b4.json` | Explicit example with optimum 92 and bipartite value 87 |
| `results/permutation_audit.json` | Independent check of the subset oracle |
| `results/sharpness.json` | Values for the explicit two-hub family |
| `results/nonbipartite_examples.json` | Further examples with strict gaps |

Recorded experiments were run on 18 October 2026 with Python 3.12.14 and
NetworkX 3.7. Timings are individual wall-clock observations on a shared
machine, not statistical performance estimates. Large instances were checked
by evaluating their returned permutations, not by the exponential oracle.
All recorded large benchmark instances happen to have bipartite optima.

## Version and license

Version **1.0.0** contains the solver and the recorded verification data.
See `CITATION.cff` for software citation metadata. The repository is distributed
under the MIT license; see `LICENSE`.
