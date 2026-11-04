# Round 3 results (2026-10-31)

Seeker-Comb v2.0 (netlist, DosStuck payload). Per-circuit table is in the generated answer_key/rareness.md; pooled below. Target band = what site selection aimed at; band = what the independent measurement shows.

| band reached | circuits |
|---|---|
| p<1e-4 | 16 |
| p<1e-3 | 20 |
| p<1e-2 | 17 |
| p>=1e-2 | 0 |
| never | 0 |

Pooled: 53 infected circuits, geometric mean p = 2.979e-04 over the 53 that fired at least once, 38437632 vectors in total.

Failures / band unreachable:
- C17 [p<1e-2]: band unreachable: best joint p 3.11e-02 with k=3 (design too small for this band)
- C17 [p<1e-3]: band unreachable: best joint p 3.11e-02 with k=3 (design too small for this band)
- C17 [p<1e-4]: band unreachable: best joint p 3.11e-02 with k=3 (design too small for this band)
- apex4 [p<1e-3]: band unreachable: best joint p 1.84e-03 with k=1 (design too small for this band)
- apex4 [p<1e-4]: band unreachable: best joint p 1.84e-03 with k=1 (design too small for this band)
- ex5p [p<1e-3]: band unreachable: best joint p 3.91e-03 with k=1 (design too small for this band)
- ex5p [p<1e-4]: band unreachable: best joint p 3.91e-03 with k=1 (design too small for this band)

Seeker-Seq v2.0 (P(trigger high within N cycles) over 2048 or 512 independent lanes):

| N cycles | circuits | with P(fire<=N)>0 | min | median | max |
|---|---|---|---|---|---|
| 16 | 80 | 4 | 0.00e+00 | 0.00e+00 | 3.91e-03 |
| 64 | 80 | 12 | 0.00e+00 | 0.00e+00 | 3.12e-01 |
| 256 | 80 | 18 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 1024 | 80 | 24 | 0.00e+00 | 0.00e+00 | 1.00e+00 |

Failures / band unreachable:
- s298 [counter3]: no quiet driven output for the payload
- s298 [counter6]: no quiet driven output for the payload
- s298 [pattern3]: no quiet driven output for the payload
- s298 [pattern5]: no quiet driven output for the payload
- s526 [counter3]: no quiet driven output for the payload
- s526 [counter6]: no quiet driven output for the payload
- s526 [pattern3]: no quiet driven output for the payload
- s526 [pattern5]: no quiet driven output for the payload
- s953 [counter3]: no quiet driven output for the payload
- s953 [counter6]: no quiet driven output for the payload
- s953 [pattern3]: no quiet driven output for the payload
- s953 [pattern5]: no quiet driven output for the payload
