# v05_04_04 DL model development result

- Selection basis: pooled expanding-time OOF only
- Selected candidate: v05_04_static
- Selected feature set: core56_dl_stable (56 features)
- OOF Macro F1: 0.5697
- OOF Macro PR-AUC: 0.5902
- Final Test Macro F1: 0.5730
- Final Test Macro PR-AUC: 0.5944
- Final Test weakened Recall: 69.36%
- Final Test stopped Recall: 40.27%
- Top 20% Precision / Recall / Lift:
  89.06% /
  29.48% /
  1.47x

The class scores are ranking scores, not calibrated churn probabilities.
ML comparison and ML-DL ensembling are outside this stage.
