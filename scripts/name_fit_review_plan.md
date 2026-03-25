# Proposed Plan: Interactive `score_name_fit` Review Script

## 1) Mirror existing review-script style
Build the new script with the same interaction and persistence pattern used by `scripts/review_phonetics_sample.py`:
- CLI arguments
- deterministic random sampling via seed
- interactive labels (`1` = good, `0` = bad, `q` = quit)
- append-per-review JSONL persistence
- end-of-run summary

---

## 2) Inputs and CLI surface
Support two surname sources:
1. file-based (e.g. `test_surnames.json`)
2. inline list (e.g. `"floegel,schaefer,mayer"`)

Recommended args:
- `--first-names-data PATH`
- `--surname-file PATH` (optional)
- `--surnames CSV` (optional)
- `--first-name-count N`
- `--seed N`
- `--language de`
- `--output-jsonl PATH`
- `--summary-json PATH`
- `--threshold 0.5`
- optional `--max-pairs N`

Validation:
- require exactly one of `--surname-file` or `--surnames`

---

## 3) Sampling + pair generation
Workflow:
1. Load first names.
2. Sample deterministic subset (`count`, `seed`).
3. Load surnames from selected source.
4. Generate Cartesian product: sampled first names × surnames.
5. Optionally shuffle order (same seed) and apply `--max-pairs` cap.
6. For each pair:
   - compute `score_name_fit(first_name, surname, language)`
   - prompt reviewer for `1/0/q`

---

## 4) Persistence schema (JSONL)
Persist each reviewed pair immediately for resumability and post-analysis.

Suggested per-record fields:
- metadata: `timestamp`, `session_id`, optional `reviewer`
- pair: `first_name`, `surname`, `language`
- heuristic outputs: `overall_score`, `overall_score_percent`, `component_scores`, `feature_values`
- human review: `human_label` (0/1)
- derived: `threshold`, `predicted_label`, `score_likelihood`, `is_correct`
- optional: `notes`

Why JSONL:
- append-safe
- robust for interrupted sessions
- easy downstream parsing and aggregation

---

## 5) Likelihood transform + confusion matrix
Use a transparent mapping:
- `score_likelihood = overall_score`  (already normalized to 0..1)
- `predicted_label = 1 if score_likelihood >= threshold else 0`

Then calculate confusion matrix:
- TP, FP, TN, FN

And standard metrics:
- accuracy
- precision
- recall
- F1
- specificity
- balanced accuracy

---

## 6) End-of-run outputs
Produce two outputs:
1. **Raw JSONL**: one line per reviewed pair
2. **Summary JSON** with:
   - total sampled first names
   - total surnames
   - total generated pairs
   - reviewed pairs
   - class balance (`good`, `bad`)
   - confusion matrix
   - metrics
   - threshold used
   - quit/resume info

Console summary can print the same key metrics for quick feedback.

---

## 7) Test plan
Add deterministic tests for helper functions and score/label composition:
- loading first names and surnames from supported input shapes
- inline surname CSV parsing
- deterministic sampling with seed
- pair generation size/content
- threshold-based class prediction
- confusion matrix correctness on fixed fixtures
- summary payload correctness
- append JSONL record validity

Keep interactive I/O minimal in tests; focus on pure helper functions.

---

## Potential improvements
1. **Resume and deduplicate**: skip already reviewed `(first_name, surname)` pairs.
2. **Score-band sampling**: intentionally sample low/mid/high heuristic scores for better calibration data.
3. **Threshold sweep utility**: evaluate metrics over a threshold grid and suggest best operating point.
4. **Calibration diagnostics**: bucket scores and compare empirical hit-rates.
5. **Error-analysis exports**: separate FN/FP slices with feature/component details.
6. **Schema versioning**: include `schema_version` in each record.
7. **Inter-rater agreement**: support multiple reviewers and calculate agreement metrics.

---

## Note
This plan is intentionally aligned with the existing review helper style (`scripts/review_phonetics_sample.py` + its tests), so implementation effort stays low while output quality remains audit-friendly.

---

## Commands used to prepare this plan
```bash
sed -n '1,260p' scripts/review_phonetics_sample.py
sed -n '1,260p' tests/test_review_phonetics_sample.py
rg --files data | sed -n '1,120p'
find . -maxdepth 2 -type d | sed -n '1,120p'
```
