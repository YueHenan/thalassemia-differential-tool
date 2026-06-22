#!/usr/bin/env python3
"""
IDA/THA鉴别计算器 - 基于Top 10公式投票法（双语版）
IDA/THA Differential Calculator - Based on Top 10 Formula Voting Method (Bilingual)

核心功能：
1. 使用AUC排名前10的公式进行计算
2. 投票法阈值≥4判定为地中海贫血（特异度97.4%）
3. DF公式单独判断（AUC=0.8599，优化阈值>3.0）
4. 保留数据库和导出功能（PDF/Excel）
5. 支持中英文切换
"""

import tkinter as tk
import math
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
from typing import Dict, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
import os

# 延迟加载的模块（仅用于类型检查）
if TYPE_CHECKING:
    from database import ScreeningDatabase
    from export import ExportManager


# ============================================================================
# 双语翻译字典
# ============================================================================
TRANSLATIONS = {
    'zh': {
        # 标题
        'window_title': "IDA/THA鉴别计算器 | 联合策略版 (Top 5 + Distill)",
        'main_title': "IDA/THA鉴别计算器 | 联合策略版",
        'subtitle': "联合策略：Top 5投票(≥2) 或 Distill公式(>0.569) | 敏感度84.2% 特异度85.5%",
        
        # 患者信息
        'patient_info': "患者信息 (可选)",
        'name': "姓名",
        'patient_id': "患者ID",
        'age': "年龄",
        'gender': "性别",
        'hometown': "籍贯",
        'test_date': "检测日期",
        'male': "男",
        'female': "女",
        
        # 血液参数
        'blood_params': "血液参数输入",
        
        # 按钮
        'calculate': "计算",
        'save': "保存",
        'export': "导出",
        'clear': "清空",
        'example': "示例",
        'lang_switch': "English",
        
        # 结果区域
        'results': "计算结果",
        'input_params': "输入参数",
        'top5_results': "Top 5公式计算结果",
        'rank': "排名",
        'formula_name': "公式名称",
        'calc_value': "计算值",
        'calc_process': "计算过程",
        'threshold': "阈值",
        'judgment': "判断",
        'population': "来源人群",
        'reference': "参考文献",
        'comprehensive': "综合判断",
        
        # 策略名称
        'voting_method': "Top 5 投票法",
        'distill_method': "Distill 公式",
        'combined_method': "联合策略 (Combined)",
        
        # 指标
        'positive_count': "阳性数",
        'probability': "概率",
        'threshold_gte2': "阈值≥2",
        'threshold_distill': "阈值>0.569",
        'diagnostic_perf': "诊断效能",
        'sensitivity': "敏感度",
        'specificity': "特异度",
        
        # 判断结果
        'suggests_tha': "提示地中海贫血 (THA)",
        'not_suggests_tha': "不提示地中海贫血",
        'tha_short': "THA",
        'ida_short': "IDA",
        
        # 结论
        'conclusion': "结论",
        'recommendation': "建议",
        'strong_suggests_tha': "强烈提示地中海贫血",
        'suggests_tha_result': "提示地中海贫血",
        'not_tha': "不提示地中海贫血 (倾向IDA)",
        'recommend_gene_test': "建议进行基因检测确诊",
        'recommend_iron_check': "考虑缺铁性贫血可能，建议检查铁代谢指标",
        
        # 注意事项
        'notes': "注意事项",
        'note1': "联合策略(Top5≥2 或 Distill>0.569)具有最高的诊断效能 (AUC=0.9198)",
        'note2': "以上结果仅供参考，确诊需进行基因检测",
        'note3': "近期有输血史的患者，公式诊断效能可能下降",
        
        # 错误消息
        'error': "错误",
        'warning': "警告",
        'param_error': "参数错误",
        'input_error': "输入错误",
        'calc_error': "计算时发生错误",
        'please_calc_first': "请先进行计算",
        'enter_valid_number': "请输入有效的数字",
        'success': "成功",
        'record_saved': "记录已保存",
        'export_success': "导出成功",
        'export_failed': "导出失败",
        'export_format': "导出格式",
        'export_pdf_question': "导出为PDF？\n(否则导出为Excel)",
        
        # 验证错误
        'mcv_range': "MCV超出范围30-150 fL",
        'rbc_range': "RBC超出范围1-10 ×10¹²/L",
        'hb_range': "Hb超出范围2-25 g/dL",
        'mch_range': "MCH超出范围10-50 pg",
        'rdw_range': "RDW超出范围5-50%",
    },
    'en': {
        # Titles
        'window_title': "IDA/THA Differential Calculator | Combined Strategy (Top 5 + Distill)",
        'main_title': "IDA/THA Differential Calculator | Combined Strategy",
        'subtitle': "Combined Strategy: Top 5 Voting(≥2) OR Distill(>0.569) | Sens 84.2% Spec 85.5%",
        
        # Patient info
        'patient_info': "Patient Information (Optional)",
        'name': "Name",
        'patient_id': "Patient ID",
        'age': "Age",
        'gender': "Gender",
        'hometown': "Hometown",
        'test_date': "Test Date",
        'male': "Male",
        'female': "Female",
        
        # Blood parameters
        'blood_params': "Blood Parameters",
        
        # Buttons
        'calculate': "Calculate",
        'save': "Save",
        'export': "Export",
        'clear': "Clear",
        'example': "Example",
        'lang_switch': "中文",
        
        # Results area
        'results': "Results",
        'input_params': "Input Parameters",
        'top5_results': "Top 5 Formula Results",
        'rank': "Rank",
        'formula_name': "Formula",
        'calc_value': "Value",
        'calc_process': "Calculation",
        'threshold': "Threshold",
        'judgment': "Result",
        'population': "Population",
        'reference': "Reference",
        'comprehensive': "Comprehensive Analysis",
        
        # Strategy Names
        'voting_method': "Top 5 Voting",
        'distill_method': "Distill Formula",
        'combined_method': "Combined Strategy",
        
        # Metrics
        'positive_count': "Positive Count",
        'probability': "Probability",
        'threshold_gte2': "Threshold ≥2",
        'threshold_distill': "Threshold >0.569",
        'diagnostic_perf': "Diagnostic Performance",
        'sensitivity': "Sensitivity",
        'specificity': "Specificity",
        
        # Judgment results
        'suggests_tha': "Suggests Thalassemia (THA)",
        'not_suggests_tha': "Does not suggest Thalassemia",
        'tha_short': "THA",
        'ida_short': "IDA",
        
        # Conclusions
        'conclusion': "Conclusion",
        'recommendation': "Recommendation",
        'strong_suggests_tha': "Strongly suggests Thalassemia",
        'suggests_tha_result': "Suggests Thalassemia",
        'not_tha': "Does not suggest Thalassemia (likely IDA)",
        'recommend_gene_test': "Recommend genetic testing for confirmation",
        'recommend_iron_check': "Consider Iron Deficiency Anemia, check iron metabolism",
        
        # Notes
        'notes': "Notes",
        'note1': "Combined Strategy (Top5≥2 OR Distill>0.569) has the highest diagnostic performance (AUC=0.9198)",
        'note2': "Results are for reference only, genetic testing required for diagnosis",
        'note3': "Diagnostic accuracy may decrease in patients with recent transfusion",
        
        # Error messages
        'error': "Error",
        'warning': "Warning",
        'param_error': "Parameter Error",
        'input_error': "Input Error",
        'calc_error': "Calculation Error",
        'please_calc_first': "Please calculate first",
        'enter_valid_number': "Please enter valid numbers",
        'success': "Success",
        'record_saved': "Record saved",
        'export_success': "Export successful",
        'export_failed': "Export failed",
        'export_format': "Export Format",
        'export_pdf_question': "Export as PDF?\n(Otherwise export as Excel)",
        
        # Validation errors
        'mcv_range': "MCV out of range 30-150 fL",
        'rbc_range': "RBC out of range 1-10 ×10¹²/L",
        'hb_range': "Hb out of range 2-25 g/dL",
        'mch_range': "MCH out of range 10-50 pg",
        'rdw_range': "RDW out of range 5-50%",
    }
}


@dataclass
class BloodParameters:
    """血液检测参数"""
    mcv: float
    rbc: float
    hb: float
    mch: float
    rdw: float
    
    @property
    def mchc(self) -> float:
        """计算MCHC"""
        return (self.mch / self.mcv) * 100 if self.mcv > 0 else 0
    
    def validate(self, lang='zh') -> tuple:
        """验证参数是否在合理范围内"""
        t = TRANSLATIONS[lang]
        errors = []
        if not (30 <= self.mcv <= 150):
            errors.append(f"MCV({self.mcv}) {t['mcv_range']}")
        if not (1 <= self.rbc <= 10):
            errors.append(f"RBC({self.rbc}) {t['rbc_range']}")
        if not (2 <= self.hb <= 25):
            errors.append(f"Hb({self.hb}) {t['hb_range']}")
        if not (10 <= self.mch <= 50):
            errors.append(f"MCH({self.mch}) {t['mch_range']}")
        if not (5 <= self.rdw <= 50):
            errors.append(f"RDW({self.rdw}) {t['rdw_range']}")
        
        if errors:
            return False, "\n".join(errors)
        return True, ""


@dataclass
class FormulaResult:
    """单个公式的计算结果"""
    rank: int
    name: str
    formula: str
    value: float
    threshold: float
    direction: str
    suggests_tha: bool
    auc: float
    population: str = ""
    year: int = 2020
    reference: str = ""
    calculation_process: str = ""
    youden: float = 0.0
    ci_value: float = 0.0
    
    @property
    def threshold_display(self) -> str:
        return f"{self.direction}{self.threshold}"


class ThalassemiaCalculator:
    """联合策略鉴别计算器 (Top 5 + Distill)"""
    
    FORMULAS = [
        {"rank": 1, "name": "DF", "auc": 0.8599, "youden": 0.5526, "ci_value": 0.8071,
         "formula": "1.109×MCH - 0.391×MCV + 1.182×RBC + 0.116×RDW",
         "threshold": 3.0, "direction": ">",
         "population": "Chinese Guangzhou", "year": 2020, "reference": "Shang (2020)"},
        {"rank": 2, "name": "Sirachainan", "auc": 0.6633, "youden": 0.3421, "ci_value": 0.2437,
         "formula": "1.5×Hb - 0.05×MCV", "threshold": 14.0, "direction": ">",
         "population": "Thai children", "year": 2014, "reference": "Sirachainan et al. (2014)"},
        {"rank": 3, "name": "MDHL", "auc": 0.6534, "youden": 0.4211, "ci_value": 0.4376,
         "formula": "MCH×RBC / MCV", "threshold": 1.75, "direction": ">",
         "population": "Saudi Arabia", "year": 1999, "reference": "Ehsani et al. (2009)"},
        {"rank": 4, "name": "England & Fraser", "auc": 0.6018, "youden": 0.4342, "ci_value": 0.4399,
         "formula": "MCV - RBC - 5×Hb - 3.4", "threshold": 0, "direction": "<",
         "population": "British", "year": 1973, "reference": "England & Fraser (1973)"},
        {"rank": 5, "name": "Green & King", "auc": 0.5972, "youden": 0.4211, "ci_value": 0.4356,
         "formula": "MCV²×RDW / (Hb×100)", "threshold": 65, "direction": "<",
         "population": "American", "year": 1989, "reference": "Green & King (1989)"},
    ]
    
    # 统一Distill阈值
    DISTILL_THRESHOLD = 0.569

    def __init__(self, params: BloodParameters):
        self.params = params
        self.p = params
    
    def calculate_all(self) -> List[FormulaResult]:
        results = []
        for f in self.FORMULAS:
            value, process = self._calculate_formula(f["rank"], f["formula"])
            suggests_tha = self._check_threshold(value, f["threshold"], f["direction"])
            results.append(FormulaResult(
                rank=f["rank"], name=f["name"], formula=f["formula"],
                value=value, threshold=f["threshold"], direction=f["direction"],
                suggests_tha=suggests_tha, auc=f["auc"],
                population=f.get("population", ""), year=f.get("year", 2020),
                reference=f.get("reference", ""),
                calculation_process=process,
                youden=f.get("youden", 0.0), ci_value=f.get("ci_value", 0.0)
            ))
        return results
    
    def _calculate_formula(self, rank: int, formula_str: str) -> tuple[float, str]:
        p = self.params
        value = 0.0
        
        # 替换变量以生成计算过程
        # 注意：这里简单的字符串替换可能不完美，但对于展示目的足够
        # 我们使用f-string手动构建过程字符串以确保格式整洁
        
        process_str = ""
        
        if rank == 1: # DF
            value = 1.109 * p.mch - 0.391 * p.mcv + 1.182 * p.rbc + 0.116 * p.rdw
            process_str = f"1.109×{p.mch} - 0.391×{p.mcv} + 1.182×{p.rbc} + 0.116×{p.rdw}"
        elif rank == 2: # Sirachainan
            value = 1.5 * p.hb - 0.05 * p.mcv
            process_str = f"1.5×{p.hb} - 0.05×{p.mcv}"
        elif rank == 3: # MDHL
            if p.mcv > 0:
                value = p.mch * p.rbc / p.mcv
                process_str = f"{p.mch}×{p.rbc} / {p.mcv}"
            else:
                value = 0
                process_str = "Error: MCV=0"
        elif rank == 4: # England & Fraser
            value = p.mcv - p.rbc - 5 * p.hb - 3.4
            process_str = f"{p.mcv} - {p.rbc} - 5×{p.hb} - 3.4"
        elif rank == 5: # Green & King
            if p.hb > 0:
                value = (p.mcv ** 2) * p.rdw / (p.hb * 100)
                process_str = f"{p.mcv}²×{p.rdw} / ({p.hb}×100)"
            else:
                value = 0
                process_str = "Error: Hb=0"
        
        return value, process_str
    
    def calculate_distill(self) -> tuple[float, float, bool, str]:
        """计算Distill公式，返回 (logits, probability, suggests_tha, process_str)"""
        p = self.params
        # Distill Formula: -5.304 + 0.728*RBC + 0.008*HB - 0.384*MCV + 1.182*MCH + 0.210*RDW
        logits = -5.304 + 0.728 * p.rbc + 0.008 * p.hb - 0.384 * p.mcv + 1.182 * p.mch + 0.210 * p.rdw
        
        # 构建计算过程字符串
        process_str = (
            f"Logits = -5.304 + 0.728×{p.rbc} + 0.008×{p.hb} - 0.384×{p.mcv} + 1.182×{p.mch} + 0.210×{p.rdw}\n"
            f"                      = {logits:.4f}\n"
            f"       Probability = 1 / (1 + e^(-{logits:.4f}))"
        )
        
        try:
            prob = 1 / (1 + math.exp(-logits))
        except OverflowError:
            prob = 1.0 if logits > 0 else 0.0
            
        suggests_tha = prob > self.DISTILL_THRESHOLD
        return logits, prob, suggests_tha, process_str

    def _check_threshold(self, value: float, threshold: float, direction: str) -> bool:
        return value > threshold if direction == ">" else value < threshold
    
    def get_voting_count(self, results: List[FormulaResult]) -> int:
        return sum(1 for r in results if r.suggests_tha)
    
    def interpret(self, results: List[FormulaResult], lang='zh') -> Dict:
        t = TRANSLATIONS[lang]
        
        # 1. Top 5 投票
        vote_count = self.get_voting_count(results)
        voting_threshold = 2
        voting_suggests_tha = vote_count >= voting_threshold
        
        # 2. Distill 公式
        distill_logits, distill_prob, distill_suggests_tha, distill_process = self.calculate_distill()
        
        # 3. 联合策略 (Combined Strategy)
        # Logic: Top 5 >= 2 OR Distill > 0.569
        combined_suggests_tha = voting_suggests_tha or distill_suggests_tha
        
        # 结论判定
        level = "low"
        if combined_suggests_tha:
            if voting_suggests_tha and distill_suggests_tha:
               conclusion = t['strong_suggests_tha']
               recommendation = t['recommend_gene_test']
               level = "high"
            else:
               conclusion = t['suggests_tha_result']
               recommendation = t['recommend_gene_test']
               level = "high" # 只要联合策略阳性，就提示地贫
        else:
            conclusion = t['not_tha']
            recommendation = t['recommend_iron_check']
            level = "low"
        
        return {
            "vote_count": vote_count,
            "voting_suggests_tha": voting_suggests_tha,
            "distill_prob": distill_prob,
            "distill_suggests_tha": distill_suggests_tha,
            "distill_process": distill_process,
            "combined_suggests_tha": combined_suggests_tha,
            "conclusion": conclusion,
            "recommendation": recommendation,
            "level": level
        }


class DifferentialGUI:
    """IDA/THA鉴别计算器GUI（双语版）"""
    
    def __init__(self, root):
        self.root = root
        self.lang = 'zh'  # 默认中文
        self.t = TRANSLATIONS[self.lang]
        
        self.root.title(self.t['window_title'])
        self.root.geometry("1150x850")
        self.root.resizable(True, True)
        
        # 延迟加载
        self._db = None
        self._exporter = None
        
        # 当前结果
        self.current_params = None
        self.current_results = None
        self.current_interpretation = None
        self.current_record_id = None
        
        # UI元素引用（用于语言切换）
        self.ui_elements = {}
        
        self.setup_styles()
        self.create_widgets()
    
    @property
    def db(self):
        if self._db is None:
            try:
                from database import ScreeningDatabase
                self._db = ScreeningDatabase()
            except ImportError:
                messagebox.showwarning(self.t['warning'], "Database module not found")
                return None
        return self._db
    
    @property
    def exporter(self):
        if self._exporter is None:
            try:
                from export import ExportManager
                self._exporter = ExportManager()
            except ImportError:
                messagebox.showwarning(self.t['warning'], "Export module not found")
                return None
        return self._exporter
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'), foreground='#2c3e50')
        style.configure('Info.TLabel', foreground='#3498db', font=('Arial', 10))
        style.configure('Compact.TButton', font=('Arial', 10), padding=(10, 5))
        style.configure('Lang.TButton', font=('Arial', 9, 'bold'), padding=(8, 4))
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # 标题行（包含语言切换按钮）
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        title_frame.columnconfigure(0, weight=1)
        
        self.title_label = ttk.Label(title_frame, text=self.t['main_title'], style='Title.TLabel')
        self.title_label.grid(row=0, column=0)
        self.ui_elements['title'] = self.title_label
        
        self.lang_btn = ttk.Button(title_frame, text=self.t['lang_switch'], 
                                   command=self.toggle_language, style='Lang.TButton')
        self.lang_btn.grid(row=0, column=1, padx=(20, 0))
        self.ui_elements['lang_btn'] = self.lang_btn
        
        self.subtitle_label = ttk.Label(main_frame, text=self.t['subtitle'], style='Info.TLabel')
        self.subtitle_label.grid(row=1, column=0, pady=(0, 5))
        self.ui_elements['subtitle'] = self.subtitle_label
        
        # 患者信息
        self.create_patient_frame(main_frame)
        
        # 血液参数
        self.create_input_frame(main_frame)
        
        # 结果区域
        self.create_result_frame(main_frame)
    
    def create_patient_frame(self, parent):
        self.patient_frame = ttk.LabelFrame(parent, text=self.t['patient_info'], padding="5")
        self.patient_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        self.ui_elements['patient_frame'] = self.patient_frame
        
        self.patient_entries = {}
        self.patient_labels = {}
        
        patient_fields = [
            ('name', 'name', ''),
            ('id', 'patient_id', ''),
            ('age', 'age', ''),
            ('gender', 'gender', ''),
            ('hometown', 'hometown', ''),
            ('test_date', 'test_date', datetime.now().strftime('%Y-%m-%d'))
        ]
        
        for i, (key, label_key, placeholder) in enumerate(patient_fields):
            lbl = ttk.Label(self.patient_frame, text=f"{self.t[label_key]}:", font=('Arial', 9))
            lbl.grid(row=0, column=i*2, sticky=tk.W, padx=(5, 2))
            self.patient_labels[key] = (lbl, label_key)
            
            if key == 'gender':
                entry = ttk.Combobox(self.patient_frame, width=8,
                                    values=[self.t['male'], self.t['female'], ''])
                entry.set('')
            else:
                entry = ttk.Entry(self.patient_frame, width=12)
                if placeholder:
                    entry.insert(0, placeholder)
            
            entry.grid(row=0, column=i*2+1, sticky=(tk.W, tk.E), padx=(0, 8))
            self.patient_entries[key] = entry
    
    def create_input_frame(self, parent):
        self.input_frame = ttk.LabelFrame(parent, text=self.t['blood_params'], padding="5")
        self.input_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        self.ui_elements['input_frame'] = self.input_frame
        
        self.entries = {}
        parameters = [('mcv', 'MCV', 'fL'), ('rbc', 'RBC', '×10¹²/L'),
                     ('hb', 'Hb', 'g/dL'), ('mch', 'MCH', 'pg'), ('rdw', 'RDW', '%')]
        
        for i, (key, label, unit) in enumerate(parameters):
            ttk.Label(self.input_frame, text=f"{label}:", font=('Arial', 10)).grid(
                row=0, column=i*3, padx=(10, 2))
            entry = ttk.Entry(self.input_frame, width=8)
            entry.grid(row=0, column=i*3+1, padx=2)
            self.entries[key] = entry
            ttk.Label(self.input_frame, text=unit, font=('Arial', 9), foreground='gray').grid(
                row=0, column=i*3+2, padx=(0, 10))
        
        # 按钮
        btn_frame = ttk.Frame(self.input_frame)
        btn_frame.grid(row=0, column=15, padx=(20, 0))
        
        self.btn_calc = ttk.Button(btn_frame, text=self.t['calculate'], 
                                   command=self.calculate, style='Compact.TButton')
        self.btn_calc.pack(side=tk.LEFT, padx=2)
        self.ui_elements['btn_calc'] = self.btn_calc
        
        self.btn_save = ttk.Button(btn_frame, text=self.t['save'],
                                   command=self.save_record, style='Compact.TButton')
        self.btn_save.pack(side=tk.LEFT, padx=2)
        self.ui_elements['btn_save'] = self.btn_save
        
        self.btn_export = ttk.Button(btn_frame, text=self.t['export'],
                                     command=self.export_result, style='Compact.TButton')
        self.btn_export.pack(side=tk.LEFT, padx=2)
        self.ui_elements['btn_export'] = self.btn_export
        
        self.btn_clear = ttk.Button(btn_frame, text=self.t['clear'],
                                    command=self.clear_inputs, style='Compact.TButton')
        self.btn_clear.pack(side=tk.LEFT, padx=2)
        self.ui_elements['btn_clear'] = self.btn_clear
        
        self.btn_example = ttk.Button(btn_frame, text=self.t['example'],
                                      command=self.load_example, style='Compact.TButton')
        self.btn_example.pack(side=tk.LEFT, padx=2)
        self.ui_elements['btn_example'] = self.btn_example
    
    def create_result_frame(self, parent):
        self.result_frame = ttk.LabelFrame(parent, text=self.t['results'], padding="10")
        self.result_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.rowconfigure(0, weight=1)
        self.ui_elements['result_frame'] = self.result_frame
        
        self.result_text = scrolledtext.ScrolledText(
            self.result_frame, wrap=tk.WORD, width=100, height=25,
            font=('Consolas', 9), state='disabled'
        )
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.result_text.tag_configure('header', font=('Arial', 11, 'bold'), foreground='#2c3e50')
        self.result_text.tag_configure('tha', foreground='#e74c3c', font=('Consolas', 9, 'bold'))
        self.result_text.tag_configure('ida', foreground='#27ae60', font=('Consolas', 9, 'bold'))
        self.result_text.tag_configure('info', foreground='#3498db')
    
    def toggle_language(self):
        """切换语言"""
        self.lang = 'en' if self.lang == 'zh' else 'zh'
        self.t = TRANSLATIONS[self.lang]
        self.update_ui_language()
        
        # 如果有结果，重新显示
        if self.current_params and self.current_results:
            calculator = ThalassemiaCalculator(self.current_params)
            self.current_interpretation = calculator.interpret(self.current_results, self.lang)
            self.display_results(self.current_params, self.current_results, self.current_interpretation)
    
    def update_ui_language(self):
        """更新所有UI元素的语言"""
        self.root.title(self.t['window_title'])
        
        # 标题
        self.title_label.config(text=self.t['main_title'])
        self.subtitle_label.config(text=self.t['subtitle'])
        self.lang_btn.config(text=self.t['lang_switch'])
        
        # 框架标题
        self.patient_frame.config(text=self.t['patient_info'])
        self.input_frame.config(text=self.t['blood_params'])
        self.result_frame.config(text=self.t['results'])
        
        # 患者信息标签
        for key, (lbl, label_key) in self.patient_labels.items():
            lbl.config(text=f"{self.t[label_key]}:")
        
        # 更新性别下拉框
        gender_entry = self.patient_entries['gender']
        current_val = gender_entry.get()
        gender_entry['values'] = [self.t['male'], self.t['female'], '']
        # 转换当前值
        if current_val in ['男', 'Male']:
            gender_entry.set(self.t['male'])
        elif current_val in ['女', 'Female']:
            gender_entry.set(self.t['female'])
        
        # 按钮
        self.btn_calc.config(text=self.t['calculate'])
        self.btn_save.config(text=self.t['save'])
        self.btn_export.config(text=self.t['export'])
        self.btn_clear.config(text=self.t['clear'])
        self.btn_example.config(text=self.t['example'])
    
    def get_input_values(self) -> BloodParameters:
        try:
            return BloodParameters(
                mcv=float(self.entries['mcv'].get()),
                rbc=float(self.entries['rbc'].get()),
                hb=float(self.entries['hb'].get()),
                mch=float(self.entries['mch'].get()),
                rdw=float(self.entries['rdw'].get())
            )
        except ValueError:
            raise ValueError(self.t['enter_valid_number'])
    
    def calculate(self):
        try:
            params = self.get_input_values()
            is_valid, error_msg = params.validate(self.lang)
            if not is_valid:
                messagebox.showerror(self.t['param_error'], error_msg)
                return
            
            calculator = ThalassemiaCalculator(params)
            results = calculator.calculate_all()
            interpretation = calculator.interpret(results, self.lang)
            
            self.current_params = params
            self.current_results = results
            self.current_interpretation = interpretation
            
            self.display_results(params, results, interpretation)
            
        except ValueError as e:
            messagebox.showerror(self.t['input_error'], str(e))
        except Exception as e:
            messagebox.showerror(self.t['error'], f"{self.t['calc_error']}: {str(e)}")
    
    def display_results(self, params: BloodParameters, results: List[FormulaResult], 
                       interpretation: Dict):
        t = self.t
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        
        # 输入参数
        self.result_text.insert(tk.END, "═" * 90 + "\n", 'header')
        self.result_text.insert(tk.END, f"{t['input_params']}\n", 'header')
        self.result_text.insert(tk.END, "═" * 90 + "\n\n")
        self.result_text.insert(tk.END, 
            f"  MCV = {params.mcv} fL | RBC = {params.rbc} ×10¹²/L | Hb = {params.hb} g/dL | "
            f"MCH = {params.mch} pg | RDW = {params.rdw}%\n\n")
        
        # Top 5结果
        self.result_text.insert(tk.END, "═" * 90 + "\n", 'header')
        self.result_text.insert(tk.END, f"{t['top5_results']}\n", 'header')
        self.result_text.insert(tk.END, "═" * 90 + "\n\n")
        
        self.result_text.insert(tk.END, 
            f"{t['rank']:<6} {t['formula_name']:<18} {'AUC':<8} {t['calc_value']:<12} {t['judgment']:<8} {t['population']:<18} {t['reference']:<20}\n")
        self.result_text.insert(tk.END, "-" * 110 + "\n")
        
        for r in results:
            result_str = f"✓ {t['tha_short']}" if r.suggests_tha else f"✗ {t['ida_short']}"
            tag = 'tha' if r.suggests_tha else 'ida'
            # 截断过长的人群和文献文本
            pop_text = (r.population[:16] + '..') if len(r.population) > 16 else r.population
            ref_text = (r.reference[:25] + '..') if len(r.reference) > 25 else r.reference
            
            line = f"#{r.rank:<5} {r.name:<18} {r.auc:<8.4f} {r.value:<12.4f} {result_str:<8} {pop_text:<18} {ref_text:<20}"
            
            self.result_text.insert(tk.END, f"#{r.rank:<5} {r.name:<18} {r.auc:<8.4f} {r.value:<12.4f} ")
            self.result_text.insert(tk.END, f"{result_str:<9}", tag) # 结果带颜色
            self.result_text.insert(tk.END, f"{pop_text:<19} {ref_text:<20}\n")
            
            # 显示计算过程 (新行，缩进)
            self.result_text.insert(tk.END, f"       └─ {t['formula_name']}: {r.formula}\n", 'info')
            self.result_text.insert(tk.END, f"       └─ {t['calc_process']}: {r.calculation_process} = {r.value:.4f}\n", 'info')
            self.result_text.insert(tk.END, "\n")
        
        self.result_text.insert(tk.END, "\n")
        
        # 综合判断
        self.result_text.insert(tk.END, "═" * 90 + "\n", 'header')
        self.result_text.insert(tk.END, f"{t['comprehensive']}\n", 'header')
        self.result_text.insert(tk.END, "═" * 90 + "\n\n")
        
        # 1. 投票法
        vote_count = interpretation['vote_count']
        vote_tag = 'tha' if interpretation['voting_suggests_tha'] else 'ida'
        vote_result = t['suggests_tha'] if interpretation['voting_suggests_tha'] else t['not_suggests_tha']
        self.result_text.insert(tk.END, f"  【{t['voting_method']}】 {t['positive_count']}: {vote_count}/5 ({t['threshold_gte2']}) → ")
        self.result_text.insert(tk.END, f"{vote_result}\n", vote_tag)
        self.result_text.insert(tk.END, f"             {t['diagnostic_perf']}: AUC≈0.86, {t['sensitivity']}81.6%, {t['specificity']}73.7%\n\n", 'info')
        
        # 2. Distill 公式
        distill_prob = interpretation['distill_prob']
        dist_process = interpretation['distill_process']
        dist_tag = 'tha' if interpretation['distill_suggests_tha'] else 'ida'
        dist_result = t['suggests_tha'] if interpretation['distill_suggests_tha'] else t['not_suggests_tha']
        self.result_text.insert(tk.END, f"  【{t['distill_method']}】 {t['probability']}: {distill_prob:.4f} ({t['threshold_distill']}) → ")
        self.result_text.insert(tk.END, f"{dist_result}\n", dist_tag)
        
        # 显示Distill计算过程
        self.result_text.insert(tk.END, f"       {t['calc_process']}:\n", 'info')
        for line in dist_process.split('\n'):
            self.result_text.insert(tk.END, f"       {line}\n", 'info')
        
        self.result_text.insert(tk.END, f"             {t['diagnostic_perf']}: AUC=0.8963, {t['sensitivity']}81.6%, {t['specificity']}85.5%, Youden=0.671\n\n", 'info')

        # 3. 联合策略 (Combined)
        combined_tag = 'tha' if interpretation['combined_suggests_tha'] else 'ida'
        combined_result = t['suggests_tha'] if interpretation['combined_suggests_tha'] else t['not_suggests_tha']
        self.result_text.insert(tk.END, f"  【{t['combined_method']}】 {t['voting_method']} OR {t['distill_method']} → ")
        self.result_text.insert(tk.END, f"{combined_result}\n", combined_tag)
        self.result_text.insert(tk.END, f"             {t['diagnostic_perf']}: AUC=0.9198, {t['sensitivity']}84.2%, {t['specificity']}85.5%, Youden=0.697\n\n", 'info')
        
        # 结论
        self.result_text.insert(tk.END, "-" * 90 + "\n")
        level = interpretation['level']
        tag = 'tha' if level == 'high' else ('info' if level == 'medium' else 'ida')
        self.result_text.insert(tk.END, f"  ★ {t['conclusion']}: ", 'header')
        self.result_text.insert(tk.END, f"{interpretation['conclusion']}\n", tag)
        self.result_text.insert(tk.END, f"  ★ {t['recommendation']}: {interpretation['recommendation']}\n\n")
        
        # 注意事项
        self.result_text.insert(tk.END, "-" * 90 + "\n")
        self.result_text.insert(tk.END, f"  ⚠ {t['notes']}:\n", 'header')
        self.result_text.insert(tk.END, f"     • {t['note1']}\n")
        self.result_text.insert(tk.END, f"     • {t['note2']}\n")
        self.result_text.insert(tk.END, f"     • {t['note3']}\n")
        
        self.result_text.config(state='disabled')
    
    def save_record(self):
        if not self.current_params or not self.current_results:
            messagebox.showwarning(self.t['warning'], self.t['please_calc_first'])
            return
        
        # 尝试使用数据库保存
        try:
            if self.db:
                patient_name = self.patient_entries['name'].get().strip()
                patient_id = self.patient_entries['id'].get().strip()
                age_str = self.patient_entries['age'].get().strip()
                age = int(age_str) if age_str else None
                gender = self.patient_entries['gender'].get().strip()
                hometown = self.patient_entries['hometown'].get().strip()
                test_date = self.patient_entries['test_date'].get().strip()
                
                results_for_db = []
                for r in self.current_results:
                    results_for_db.append({
                        'name': r.name, 'name_en': r.name, 'value': r.value,
                        'threshold': r.threshold, 'operator': r.direction,
                        'suggests_thalassemia': r.suggests_tha, 'reference': '',
                        'year': r.year, 'ci_value': r.ci_value, 'youden': r.youden,
                        'rank': r.rank, 'formula': r.formula, 'population': r.population,
                        'calculation_process': ''
                    })
                
                from thalassemia_calculator import BloodParameters as OrigParams
                orig_params = OrigParams(
                    mcv=self.current_params.mcv, rbc=self.current_params.rbc,
                    hb=self.current_params.hb, mch=self.current_params.mch,
                    rdw=self.current_params.rdw)
                
                record_id = self.db.save_screening(
                    params=orig_params, results=results_for_db, patient_name=patient_name,
                    patient_id=patient_id, age=age, gender=gender, hometown=hometown,
                    test_date=test_date if test_date else None)
                
                self.current_record_id = record_id
                messagebox.showinfo(self.t['success'], f"{self.t['record_saved']} (ID: {record_id})")
            else:
                # 备用：保存到文本文件
                self._save_to_text()
        except Exception as e:
            # 备用：保存到文本文件
            self._save_to_text()
    
    def _save_to_text(self):
        """备用文本保存"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                self._export_to_text(filename)
            except Exception as e:
                messagebox.showerror(self.t['error'], str(e))
    
    def export_result(self):
        if not self.current_params or not self.current_results:
            messagebox.showwarning(self.t['warning'], self.t['please_calc_first'])
            return
        
        export_type = messagebox.askquestion(self.t['export_format'], 
                                             self.t['export_pdf_question'], icon='question')
        
        if export_type == 'yes':
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
            if filename:
                # 使用自己的双语PDF导出
                self._export_to_pdf(filename)
        else:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")])
            if filename:
                if filename.endswith('.xlsx') and self.exporter:
                    record = self._build_record_dict()
                    if self.exporter.export_to_excel([record], filename):
                        messagebox.showinfo(self.t['success'], f"{self.t['export_success']}: {filename}")
                    else:
                        csv_file = filename.replace('.xlsx', '.csv')
                        self._export_to_csv(csv_file)
                else:
                    csv_file = filename if filename.endswith('.csv') else filename.replace('.xlsx', '.csv')
                    self._export_to_csv(csv_file)
    
    def _export_to_pdf(self, filename: str):
        """双语PDF导出"""
        t = self.t
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import platform
            
            # 注册中文字体
            font_registered = False
            if platform.system() == 'Windows':
                for font_path in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
                    if os.path.exists(font_path):
                        try:
                            if font_path.endswith('.ttc'):
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                            else:
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_registered = True
                            break
                        except:
                            pass
            
            font_name = 'ChineseFont' if font_registered else 'Helvetica'
            
            doc = SimpleDocTemplate(filename, pagesize=A4,
                                   topMargin=0.5*inch, bottomMargin=0.5*inch,
                                   leftMargin=0.5*inch, rightMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()
            
            # 标题样式
            title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                        fontSize=16, textColor=colors.HexColor('#2c3e50'),
                                        spaceAfter=15, alignment=1, fontName=font_name)
            normal_style = ParagraphStyle('Normal', fontName=font_name, fontSize=10)
            
            # 标题
            if self.lang == 'zh':
                story.append(Paragraph("IDA/THA鉴别计算报告", title_style))
            else:
                story.append(Paragraph("IDA/THA Differential Calculation Report", title_style))
            story.append(Spacer(1, 0.1*inch))
            
            # 患者信息
            patient_data = [
                [t['patient_info'], ''],
                [t['name'] + ':', self.patient_entries['name'].get()],
                [t['patient_id'] + ':', self.patient_entries['id'].get()],
                [t['age'] + ':', self.patient_entries['age'].get()],
                [t['gender'] + ':', self.patient_entries['gender'].get()],
                [t['test_date'] + ':', datetime.now().strftime('%Y-%m-%d')]
            ]
            patient_table = Table(patient_data, colWidths=[2.5*inch, 3*inch])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ]))
            story.append(patient_table)
            story.append(Spacer(1, 0.15*inch))
            
            # 血液参数
            p = self.current_params
            blood_title = t['input_params'] if self.lang == 'zh' else "Blood Parameters"
            blood_data = [
                [blood_title, '', '', ''],
                ['MCV', f"{p.mcv} fL", 'RBC', f"{p.rbc} ×10¹²/L"],
                ['Hb', f"{p.hb} g/dL", 'MCH', f"{p.mch} pg"],
                ['RDW', f"{p.rdw}%", '', '']
            ]
            blood_table = Table(blood_data, colWidths=[1.2*inch, 1.5*inch, 1.2*inch, 1.5*inch])
            blood_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('SPAN', (0, 0), (-1, 0)),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            story.append(blood_table)
            story.append(Spacer(1, 0.15*inch))
            
            # Top 5公式结果
            result_title = t['top5_results']
            tha_text = t['tha_short']
            ida_text = t['ida_short']
            pop_header = t['population']
            ref_header = t['reference']
            
            result_header = [t['rank'], t['formula_name'], 'AUC', t['threshold'], t['calc_value'], t['judgment'], pop_header, ref_header]
            result_data = [result_header]
            for r in self.current_results:
                result_str = f"✓ {tha_text}" if r.suggests_tha else f"✗ {ida_text}"
                result_data.append([f"#{r.rank}", r.name, f"{r.auc:.3f}", r.threshold_display,
                                   f"{r.value:.2f}", result_str, r.population, r.reference])
            
            # 调整列宽以容纳更多列 (总宽度 ~7.5 inch)
            result_table = Table(result_data, colWidths=[0.4*inch, 1.2*inch, 0.5*inch, 0.6*inch, 0.6*inch, 0.6*inch, 1.1*inch, 1.8*inch])
            result_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (6, 1), (-1, -1), 'LEFT'), # 人群和文献左对齐
            ]
            # 添加THA/IDA颜色（第6列，索引5）
            for i, r in enumerate(self.current_results, 1):
                if r.suggests_tha:
                    result_style.append(('TEXTCOLOR', (5, i), (5, i), colors.red))
                else:
                    result_style.append(('TEXTCOLOR', (5, i), (5, i), colors.green))
            
            result_table.setStyle(TableStyle(result_style))
            story.append(Paragraph(f"<b>{result_title}</b>", normal_style))
            story.append(Spacer(1, 0.05*inch))
            story.append(result_table)
            story.append(Spacer(1, 0.15*inch))
            
            # 综合判断
            interp = self.current_interpretation
            vote_result = t['suggests_tha'] if interp['voting_suggests_tha'] else t['not_suggests_tha']
            distill_result = t['suggests_tha'] if interp['distill_suggests_tha'] else t['not_suggests_tha']
            combined_result = t['suggests_tha'] if interp['combined_suggests_tha'] else t['not_suggests_tha']
            
            summary_title = t['comprehensive']
            summary_data = [
                [summary_title, '', ''],
                [t['voting_method'], f"{interp['vote_count']}/5 ({t['threshold_gte2']})", vote_result],
                [t['distill_method'], f"{interp['distill_prob']:.4f} ({t['threshold_distill']})", distill_result],
                [t['combined_method'], f"Voting OR Distill", combined_result],
                [t['conclusion'], interp['conclusion'], ''],
                [t['recommendation'], interp['recommendation'], '']
            ]
            summary_table = Table(summary_data, colWidths=[1.5*inch, 2.5*inch, 2*inch])
            summary_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('SPAN', (0, 0), (-1, 0)),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, 3), colors.lightyellow), # Data rows
                ('BACKGROUND', (0, 4), (-1, -1), colors.lightgrey), # Conclusion rows
            ]
            # 结果颜色着色
            # 投票结果
            if interp['voting_suggests_tha']:
                summary_style.append(('TEXTCOLOR', (2, 1), (2, 1), colors.red))
            else:
                summary_style.append(('TEXTCOLOR', (2, 1), (2, 1), colors.green))
            # Distill结果
            if interp['distill_suggests_tha']:
                summary_style.append(('TEXTCOLOR', (2, 2), (2, 2), colors.red))
            else:
                summary_style.append(('TEXTCOLOR', (2, 2), (2, 2), colors.green))
             # Combined结果
            if interp['combined_suggests_tha']:
                summary_style.append(('TEXTCOLOR', (2, 3), (2, 3), colors.red))
            else:
                summary_style.append(('TEXTCOLOR', (2, 3), (2, 3), colors.green))
            
            summary_table.setStyle(TableStyle(summary_style))
            story.append(summary_table)
            story.append(Spacer(1, 0.15*inch))
            
            # 注意事项
            notes_text = f"<b>{t['notes']}:</b><br/>• {t['note1']}<br/>• {t['note2']}<br/>• {t['note3']}"
            story.append(Paragraph(notes_text, normal_style))
            
            doc.build(story)
            messagebox.showinfo(self.t['success'], f"{self.t['export_success']}: {filename}")
            
        except ImportError:
            # 如果没有reportlab，使用文本导出
            txt_file = filename.replace('.pdf', '.txt')
            self._export_to_text(txt_file)
        except Exception as e:
            messagebox.showerror(self.t['error'], f"{self.t['export_failed']}: {str(e)}")
    
    def _export_to_text(self, filename: str):
        """双语文本导出"""
        t = self.t
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # 标题
                if self.lang == 'zh':
                    f.write("IDA/THA鉴别计算结果\n")
                else:
                    f.write("IDA/THA Differential Calculation Results\n")
                f.write(f"{t['test_date']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                # 患者信息
                f.write(f"{t['patient_info']}:\n")
                f.write(f"  {t['name']}: {self.patient_entries['name'].get()}\n")
                f.write(f"  {t['patient_id']}: {self.patient_entries['id'].get()}\n")
                f.write(f"  {t['age']}: {self.patient_entries['age'].get()}\n")
                f.write(f"  {t['gender']}: {self.patient_entries['gender'].get()}\n")
                f.write("\n")
                
                # 输入参数
                f.write(f"{t['input_params']}:\n")
                p = self.current_params
                f.write(f"  MCV={p.mcv}fL, RBC={p.rbc}, Hb={p.hb}g/dL, MCH={p.mch}pg, RDW={p.rdw}%\n\n")
                
                # Top 10结果
                f.write(f"{t['top10_results']}:\n")
                for r in self.current_results:
                    result = t['tha_short'] if r.suggests_tha else t['ida_short']
                    f.write(f"  #{r.rank} {r.name}: {r.value:.4f} ({r.threshold_display}) → {result}\n")
                
                # 综合判断
                interp = self.current_interpretation
                f.write(f"\n{t['comprehensive']}:\n")
                vote_result = t['suggests_tha'] if interp['voting_suggests_tha'] else t['not_suggests_tha']
                df_result = t['suggests_tha'] if interp['df_suggests_tha'] else t['not_suggests_tha']
                f.write(f"  {t['voting_method']}: {interp['vote_count']}/10 → {vote_result}\n")
                f.write(f"  {t['df_formula']}: {interp['df_value']:.4f} → {df_result}\n")
                f.write(f"\n  {t['conclusion']}: {interp['conclusion']}\n")
                f.write(f"  {t['recommendation']}: {interp['recommendation']}\n")
                
                # 注意事项
                f.write(f"\n{t['notes']}:\n")
                f.write(f"  • {t['note1']}\n")
                f.write(f"  • {t['note2']}\n")
                f.write(f"  • {t['note3']}\n")
            
            messagebox.showinfo(self.t['success'], f"{self.t['export_success']}: {filename}")
        except Exception as e:
            messagebox.showerror(self.t['error'], f"{self.t['export_failed']}: {str(e)}")
    
    def _export_to_csv(self, filename: str):
        """双语CSV导出"""
        t = self.t
        try:
            with open(filename, 'w', encoding='utf-8-sig') as f:
                # 头部
                f.write(f"{t['rank']},{t['formula_name']},AUC,{t['calc_value']},{t['threshold']},{t['judgment']}\n")
                for r in self.current_results:
                    result = t['tha_short'] if r.suggests_tha else t['ida_short']
                    f.write(f"{r.rank},{r.name},{r.auc},{r.value:.4f},{r.threshold_display},{result}\n")
            
            messagebox.showinfo(self.t['success'], f"{self.t['export_success']}: {filename}")
        except Exception as e:
            messagebox.showerror(self.t['error'], f"{self.t['export_failed']}: {str(e)}")
    
    def _build_record_dict(self) -> Dict:
        patient_name = self.patient_entries['name'].get().strip()
        patient_id = self.patient_entries['id'].get().strip()
        age_str = self.patient_entries['age'].get().strip()
        age = int(age_str) if age_str else None
        gender = self.patient_entries['gender'].get().strip()
        test_date = self.patient_entries['test_date'].get().strip()
        
        results_list = []
        for r in self.current_results:
            results_list.append({
                'name': r.name, 'name_en': r.name, 'value': r.value,
                'threshold': r.threshold, 'operator': r.direction,
                'suggests_thalassemia': r.suggests_tha, 'reference': '',
                'year': r.year, 'ci_value': r.ci_value, 'youden': r.youden,
                'rank': r.rank, 'formula': r.formula, 'population': r.population
            })
        
        return {
            'id': self.current_record_id or 0,
            'patient_name': patient_name, 'patient_id': patient_id,
            'age': age, 'gender': gender,
            'test_date': test_date if test_date else datetime.now().strftime('%Y-%m-%d'),
            'screening_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mcv': self.current_params.mcv, 'rbc': self.current_params.rbc,
            'hb': self.current_params.hb, 'mch': self.current_params.mch,
            'rdw': self.current_params.rdw,
            'results': results_list,
            'positive_count': sum(1 for r in self.current_results if r.suggests_tha)
        }
    
    def clear_inputs(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        for entry in self.patient_entries.values():
            if isinstance(entry, ttk.Combobox):
                entry.set('')
            else:
                entry.delete(0, tk.END)
        self.patient_entries['test_date'].insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state='disabled')
        self.current_params = None
        self.current_results = None
        self.current_interpretation = None
        self.current_record_id = None
    
    def load_example(self):
        examples = {'mcv': '65', 'rbc': '5.5', 'hb': '10.5', 'mch': '18', 'rdw': '14'}
        for key, value in examples.items():
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, value)


def main():
    root = tk.Tk()
    app = DifferentialGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

