# FloodSaathi — AI Triage Evaluation & Accuracy Benchmark

> Benchmark run on 100 diverse, multilingual distress messages (Hindi, English, Hinglish).

## 1. Executive Metrics Summary

- **Total Evaluated Cases**: 100
- **Primary Need Classification Accuracy**: **91.0%** (Baseline: $\ge 70\%$)
- **Urgency Priority Accuracy (Bounded)**: **85.0%** (Baseline: $\ge 70\%$)
- **People Count Accuracy (Within $\pm 2$)**: **75.0%**

---

## 2. Emergency Need Confusion Matrix

| Actual \ Predicted | Rescue | Medical | Food | Shelter | Other |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Rescue** | 27 | 3 | 0 | 0 | 0 |
| **Medical** | 0 | 30 | 0 | 0 | 0 |
| **Food** | 0 | 0 | 15 | 0 | 0 |
| **Shelter** | 6 | 0 | 0 | 9 | 0 |
| **Other** | 0 | 0 | 0 | 0 | 10 |

---

## 3. Urgency Level Confusion Matrix

| Actual \ Predicted | Critical | High | Medium | Low |
| :--- | :---: | :---: | :---: | :---: |
| **Critical** | 30 | 0 | 0 | 0 |
| **High** | 6 | 21 | 3 | 0 |
| **Medium** | 0 | 6 | 24 | 0 |
| **Low** | 0 | 0 | 0 | 10 |

---

## 4. Key Performance Insights

1. **Devanagari & Hinglish Robustness**: High recall on distress phrases like *'गले तक पानी'* and *'chat par fase'*, correctly classifying critical rescue needs.
2. **Safety-Biased Urgency**: Where ambiguous, the classifier prioritizes higher urgency over lower priority to prevent under-responding in genuine emergencies.
3. **Zero-Key Determinism**: All 100 test cases run deterministically without internet latency or token consumption.
