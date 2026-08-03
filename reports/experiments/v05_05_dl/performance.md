# v05_05 Lifecycle Fusion H2 — development OOF result

- Evaluation boundary: expanding-time OOF only (validation selection years 2013–2017)
- Final Test rows loaded/predicted/evaluated: 0 / 0 / 0
- OOF Macro F1: 0.5763
- OOF Macro PR-AUC: 0.5980
- OOF balanced accuracy: 0.5714
- OOF weakened Recall: 66.76%
- OOF stopped Recall: 43.25%
- OOF retained→stopped: 319 (3.25%)
- OOF stopped→retained: 219 (5.89%)
- OOF severe error rate: 2.19%

## Same-sample OOF comparison with v05_04

- Macro F1: 0.5697 → 0.5763 (+0.0066)
- Macro PR-AUC: 0.5902 → 0.5980 (+0.0078)
- Weakened Recall: 66.63% → 66.76%
- Stopped Recall: 43.06% → 43.25%
- Severe error rate: 2.46% → 2.19%

This is a development candidate, not a newly final-Test-approved or deployed model.
The class and risk scores are ranking/model scores, not calibrated probabilities.
