# Changelog

## 2.0.0 — 26 October 2026

The final model was rederived after correction of one confirmed training-data Hb unit error: a value of 89 g/L had been analysed as 89 g/dL and was corrected to 8.9 g/dL. Version 2 replaces the earlier model coefficients and operating thresholds; it is not numerically interchangeable with version 1.

- The canonical `model.json` stores full-precision coefficients, input units, the student probability threshold and all five index rules. The new student threshold is approximately 0.532146 and DF threshold approximately 3.814560.
- DF and student thresholds are selected from training data. The revised 5-fold and 10-fold analyses repeat threshold fitting and index selection within each training partition. DF coefficients remain externally derived.
- The observed-diagnosis target and teacher-confidence weighting objective are described accurately; this is not classical soft-target distillation. Similar weighted and ordinary logistic AUCs do not establish additional benefit from teacher weighting.
- Full-cohort apparent combined performance is sensitivity 86.8%, specificity 88.2% and ranking-score AUC 0.927. These are development-cohort estimates and do not establish external validation.
- The Python GUI, local storage and every report export share one versioned prediction snapshot. Model version and SHA256 are recorded. Old performance annotations have been replaced.
- Hb units must be selected explicitly. The GUI converts g/L to g/dL and retains the original entry-range checks, so a mistyped 89 g/dL is rejected without silently changing its unit.
- Bilingual operation, optional patient fields, local saving, PDF/Excel/CSV/text exports and a synthetic example are retained; complete JSON export is added. The database uses a separate v2 location and does not silently migrate old records.
- Independent R reference vectors, strict-threshold tests, real Tk tests and native Windows executable checks accompany the release. No patient-level research records are distributed.

The prior v1.0.0 release is retained for provenance. Its coefficients and static performance text describe the historical implementation. Both versions are research tools and do not replace clinical assessment or confirmatory investigations.
