# v05_05 Lifecycle Fusion H2 — Test result

- Test structure: comparison 2017 → selection/feature cutoff 2018 → target 2019
- Test samples: 6,533
- Training range: selection years 2010–2017
- Fixed thresholds: risk 0.55, conditional stopped 0.40
- Test Macro F1: 0.5731
- Test Macro PR-AUC: 0.5962
- Test balanced accuracy: 0.5621
- Test weakened Recall: 67.86%
- Test stopped Recall: 37.56%
- Test retained→stopped: 64 (2.48%)
- Test stopped→retained: 54 (6.11%)
- Test severe error rate: 1.81%
- Test Precision@1000: 89.90%
- Test top 20% Precision/Recall/Lift: 89.29% / 29.55% / 1.48x

The model weights and thresholds were fixed before this Test evaluation.
Class and risk scores are ranking/model scores, not calibrated probabilities.
