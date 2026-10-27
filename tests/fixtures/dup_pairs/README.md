# dup_pairs: hand-labelled duplicate-code benchmark

30 pairs of Python definitions (functions/classes) from Django 5.1.4, each labelled
by hand as `duplicate` or `distinct`. Every pair is a line from the old detector's
output (`old_pairs.jsonl`, generated once from the pre-change `find_duplicates` on Django 5.1.4 and not kept here; 4987 pairs flagged because their names share tokens,
name Jaccard >= 0.6, or their docstrings share tokens, docstring Jaccard >= 0.5).
The labels were assigned by reading the code, without reference to any detector.

## Sampling

- `p01`-`p18` (`sample: random`): the first 18 pairs in `old_pairs.jsonl` order. The
  file was already randomly shuffled, so this is an unbiased sample of what the old
  detector flags. The rule was to skip any pair where either definition is longer
  than 120 lines. No pair was skipped: lines 1-18 of the file are used as they are.
- `p19`-`p30` (`sample: sought`): 12 pairs found further down `old_pairs.jsonl`
  (all after line 18) that were judged to be true duplicates. Candidates were found
  by ranking later pairs by body-text similarity, then read in full. The set covers
  exact copies (p19, p20), copies with renamed variables or calls (p21, p22, p27),
  copies with different literals or messages (p23, p24, p25, p30), a one-expression
  change between sibling backends (p26), and copies with an extra statement (p28, p29).

## File format

Each `pNN.py` starts with a header (`label`, `sample`, `a`, `b`, `why`). The two
definitions follow verbatim, dedented to top level, with their decorators and
docstrings kept. Each file parses to exactly two top-level def/class statements.

## Labelling criterion

- `duplicate`: a maintainer would want the pair flagged as the same mechanism
  implemented twice. The logic is substantially the same, so one copy could be
  deleted, or both folded into a shared helper with light parameterization.
- `distinct`: one of the following holds:
  - only the names or docstrings are similar;
  - the behavior differs;
  - the shared part is trivial boilerplate (bodies of 2 lines or less, such as
    `return self._x`, `raise NotImplementedError` or `pass`) that is not worth merging.

## Counts

| sample | duplicate | distinct |
|--------|-----------|----------|
| random (p01-p18) | 2 | 16 |
| sought (p19-p30) | 12 | 0 |
| total | 14 | 16 |

## Results

`tests/test_freshlook.py` (`test_precision_on_hand_labelled_pairs`) scores both rules on these pairs:

| rule | flagged | true duplicates | precision | recall |
|------|---------|-----------------|-----------|--------|
| old: name or docstring token Jaccard | 30 | 14 | 0.47 | 1.00 |
| new: same candidates, confirmed by AST shape | 11 | 11 | 1.00 | 0.79 |

Misses: p20, p24 and p30, short real duplicates under the 30-distinct-shingle floor. The thresholds were fixed before the
labels were read; the shape method was developed on the same Django tree, so these pairs are not fully held out.

## License

The code in these files comes from Django 5.1.4. Django is distributed under the
BSD 3-Clause license, and a copy of that license is in `LICENSE.django`.
