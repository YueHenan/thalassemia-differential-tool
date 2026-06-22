# Thalassemia Differential Diagnosis Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A Python-based Graphical User Interface (GUI) for the differential diagnosis of **Thalassemia (THA)** and **Iron Deficiency Anaemia (IDA)** using a Combined Strategy of knowledge distillation and Top 5 formula voting.

This software accompanies the manuscript:

> **Distill Formula and Top 5 Voting Formula Combined Strategy in the Differential Diagnosis of Thalassemia and Iron Deficiency Anaemia: Results from the Jiangsu Province Children's Haematology and Oncology Centre in China**
> Yongwei Yue, Peipei Chu, Chentao Shen, Hao Yuan, Yang Di, Lingjun Kong

---

## Clinical Background

Differentiating thalassemia from iron deficiency anaemia based on routine complete blood count (CBC) parameters remains a common clinical challenge, particularly in non-endemic regions. This tool implements a **Combined Strategy** that:

1. Evaluates 25 published differential formulas
2. Applies a **Top 5 voting rule** (≥ 2 positive votes → THA)
3. Applies a **Distill formula** derived via neural network knowledge distillation:

$$\text{Distill} = -5.304 + 0.728 \times \text{RBC} + 0.008 \times \text{Hb} - 0.384 \times \text{MCV} + 1.182 \times \text{MCH} + 0.210 \times \text{RDW}$$

**Decision rule:** Top 5 ≥ 2 **OR** Distill > 0.569 → Thalassemia

**Performance (full dataset, n=152):**
| Metric | Value |
|--------|-------|
| AUC | 0.920 |
| Sensitivity | 84.2% |
| Specificity | 85.5% |
| Youden Index | 0.697 |

**10-fold cross-validation (internal validation):**
| Metric | Mean ± SD |
|--------|-----------|
| AUC | 0.912 ± 0.078 |
| Sensitivity | 84.3% ± 7.9% |
| Specificity | 74.3% ± 18.5% |

---

## Installation

### Requirements
- Python 3.8 or higher
- tkinter (usually bundled with Python)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
python thalassemia_differential_gui.py
```

---

## Input Parameters

The tool requires the following CBC parameters:

| Parameter | Unit | Description |
|-----------|------|-------------|
| RBC | × 10¹²/L | Red blood cell count |
| Hb | g/dL | Haemoglobin concentration |
| MCV | fL | Mean corpuscular volume |
| MCH | pg | Mean corpuscular haemoglobin |
| RDW | % | Red cell distribution width |

---

## File Structure

```
thalassemia-differential-tool/
├── thalassemia_differential_gui.py   # Main GUI application
├── thalassemia_calculator.py          # Core formula calculation engine
├── database.py                        # Formula database (25 published indices)
├── export.py                          # Report export utilities
├── requirements.txt                   # Python dependencies
└── README.md                          # This file
```

---

## Usage Notes

> **Important:** This tool is intended as a **clinical decision support aid only**. It does not replace genetic testing, clinical judgement, or haemoglobin electrophoresis. All results should be interpreted in conjunction with the full clinical picture.

- Validated on a Chinese paediatric cohort from a tertiary haematology centre (Suzhou, Jiangsu Province, China)
- Performance may vary across populations with different prevalence and disease spectrum

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for research and clinical validation purposes, provided attribution is given to the original manuscript.

---

## Citation

If you use this tool in your research, please cite:

```
Yue Y, Chu P, Shen C, Yuan H, Di Y, Kong L. Distill Formula and Top 5 Voting Formula 
Combined Strategy in the Differential Diagnosis of Thalassemia and Iron Deficiency 
Anaemia: Results from the Jiangsu Province Children's Haematology and Oncology Centre 
in China. Anemia. 2025. [Under review]
```

---

## Contact

- **Corresponding author:** Lingjun Kong (konglingjun@suda.edu.cn)
- **Software developer:** Yongwei Yue (yywhematology@qq.com)
- **Institution:** Department of Haematology and Oncology, Children's Hospital of Soochow University, Suzhou, China
