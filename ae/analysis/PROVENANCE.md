# Analysis-script provenance

Copied read-only from the author-provided research tree on 2026-09-21. English documentation and the corrections listed below were applied to these copies. Original paths below are relative to `new_selenium/result/resubmit/`.

| Packaged filename | Original relative path |
|---|---|
| `char_new.py` | `char_new.py` |
| `draw_cdf_forward_call_num.py` | `2_forward_call/draw_cdf_forward_call_num.py` |
| `draw_forward_call_dependent.py` | `2_forward_call/draw_forward_call_dependent.py` |
| `draw_kde.py` | `1_variable_flow_depth/draw_kde.py` |
| `collect_source_scripts.py` | `4_script_char/collect_source_scripts.py` |
| `aggregate_by_category.py` | `4_script_char/aggregate_by_category.py` |
| `collboration.py` | `4_script_char/collboration.py` |

## Packaging corrections

- Pair source/path records by both domain and instance ID so different sites with the same instance number remain separate.
- Removed references to undefined counters in the forward-call CDF reader.
- Set the forward-dependence histogram default scale factor to 1 so frequencies represent actual observations.
- Corrected propagation/stack-depth labels and the direction of the paired-depth comparison in the KDE script.
- Replaced Chinese docstrings with English descriptions and removed redundant non-English comments.
