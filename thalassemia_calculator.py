"""
地中海贫血筛查计算器 (Thalassemia Screening Calculator)

该模块实现了25种地中海贫血筛查指数的计算，用于鉴别地中海贫血和缺铁性贫血。
This module implements 25 thalassemia screening indices for differentiating
thalassemia from iron deficiency anemia.

基于文献: 尚陈宇. 广州地区地中海贫血基因型分布最新调查及鉴别筛查方程的建立[D]. 广州中医药大学, 2020.
"""

from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import math


@dataclass
class BloodParameters:
    """血液检测参数 (Blood test parameters)"""
    mcv: float  # 平均红细胞体积 (Mean Corpuscular Volume, fL)
    rbc: float  # 红细胞计数 (Red Blood Cell count, x10^12/L)
    hb: float   # 血红蛋白 (Hemoglobin, g/dL)
    mch: float  # 平均红细胞血红蛋白含量 (Mean Corpuscular Hemoglobin, pg)
    rdw: float  # 红细胞分布宽度 (Red Cell Distribution Width, %)
    mchc: Optional[float] = None  # 平均红细胞血红蛋白浓度 (Mean Corpuscular Hemoglobin Concentration, g/dL)
    ret_percent: Optional[float] = None  # 网织红细胞比率 (Reticulocyte Ratio, %)

    def __post_init__(self):
        """自动计算MCHC（如果未提供）"""
        if self.mchc is None:
            # MCHC = MCH / MCV × 100
            self.mchc = (self.mch / self.mcv) * 100 if self.mcv > 0 else 0

    def validate(self) -> Tuple[bool, Optional[str]]:
        """验证参数是否在合理范围内"""
        if self.mcv <= 0 or self.mcv > 120:
            return False, "MCV应在0-120 fL范围内"
        if self.rbc <= 0 or self.rbc > 10:
            return False, "RBC应在0-10 ×10¹²/L范围内"
        if self.hb <= 0 or self.hb > 20:
            return False, "Hb应在0-20 g/dL范围内"
        if self.mch <= 0 or self.mch > 40:
            return False, "MCH应在0-40 pg范围内"
        if self.rdw <= 0 or self.rdw > 30:
            return False, "RDW应在0-30%范围内"
        if self.mchc is not None and (self.mchc <= 0 or self.mchc > 40):
            return False, "MCHC应在0-40 g/dL范围内"
        if self.ret_percent is not None and (self.ret_percent <= 0 or self.ret_percent > 10):
            return False, "RET%应在0-10%范围内"
        return True, None


@dataclass
class IndexResult:
    """单个指数的计算结果"""
    name: str           # 指数名称
    name_en: str        # 英文名称
    value: float        # 计算值
    threshold: float    # 阈值
    operator: str       # 比较运算符 ("<" 或 ">")
    suggests_thalassemia: bool  # 是否提示地贫
    reference: str      # 文献来源
    year: int          # 发表年份
    ci_value: float    # Topsis Ci值（效能指标）
    rank: int          # 效能排名
    formula: str       # 计算公式表达式
    calculation_process: str = ""  # 具体数值的计算过程
    population: str = ""  # 研究人群
    population_details: str = ""  # 研究人群详细信息（样本数量和年龄分布）


class ThalassemiaCalculator:
    """地中海贫血筛查计算器"""

    # 效能排名数据（基于Topsis Ci值）
    # 来源：尚陈宇博士论文，广州地区验证组数据
    PERFORMANCE_RANK = {
        'df': (1, 0.963),           # DF - 本研究新建
        'tidi': (2, 0.936),         # TIDI - 广西地区 (AUC=0.936)
        'green_king': (3, 0.932),   # Green & King
        'das_gupta': (4, 0.912),    # Das Gupta
        'mdhl': (5, 0.856),         # MDHL
        'england_fraser': (6, 0.823), # England & Fraser
        'huber_herklotz': (7, 0.810),
        'wongprachum': (8, 0.795),
        'sirachainan': (9, 0.780),
        'sirdah': (10, 0.765),
        'rdw_index': (11, 0.750),
        'shine_lal': (12, 0.735),
        'ehsani': (13, 0.720),
        'mentzer': (14, 0.705),
        'keikhaei': (15, 0.690),
        'nishad': (16, 0.675),
        'sehgal': (17, 0.660),
        'ricerca': (18, 0.645),
        'kerman_i': (19, 0.630),
        'kerman_ii': (20, 0.615),
        'srivastava': (21, 0.600),
        'mchd': (22, 0.585),
        'bordbar': (23, 0.570),
        'pornprasert': (24, 0.555),
        'bessman': (25, 0.540),
        'sf': (26, 0.869),          # SF - 筛查公式（单独分类）
    }

    # 文献引用
    REFERENCES = {
        'england_fraser': 'England JM, Fraser PM. Differentiation of iron deficiency from thalassaemia trait by routine blood-count. Lancet. 1973;1:449-52.',
        'mentzer': 'Mentzer Jr WC. Differentiation of iron deficiency from thalassaemia trait. Lancet. 1973;1:882.',
        'srivastava': 'Srivastava PC. Differentiation of thalassaemia minor from iron deficiency. Lancet. 1973;2:155-6.',
        'shine_lal': 'Shine I, Lal S. A strategy to detect β-thalassaemia minor. Lancet. 1977;1:692-4.',
        'bessman': 'Bessman JD, Feinstein DI. Quantitative anisocytosis as a discriminant between iron deficiency and thalassemia minor. Blood. 1979;53:288-93.',
        'ricerca': 'Ricerca BM, Storti S, d\'Onofrio G, et al. Differentiation of iron deficiency from thalassaemia trait: a new approach. Hematological. 1987;72:409-13.',
        'green_king': 'Green R, King R. A new red cell discriminant incorporating volume dispersion for differentiating iron deficiency anemia from thalassemia minor. Blood Cells. 1989;15:481-95.',
        'das_gupta': 'Das Gupta A, Hegde C, Mistri R. Red cell distribution width as a measure of severity of iron deficiency in iron deficiency anemia. Ind J Med Res. 1994;100:177-83.',
        'rdw_index': 'Jayabose S, Giamelli J, Levondoglu-Tugal O, et al. Differentiating iron deficiency anemia from thalassemia minor by using an RDW-based index. J Ped Hematol Oncol. 1999;21:314.',
        'mchd': 'Telmissani OA, Khalil S, George TR. Mean density of hemoglobin per liter of blood: a new hematologic parameter with an inherent discriminant function. Lab Hematol. 1999;5:149-52.',
        'mdhl': 'Telmissani OA, Khalil S, George TR. Mean density of hemoglobin per liter of blood: a new hematologic parameter with an inherent discriminant function. Lab Hematol. 1999;5:149-52.',
        'huber_herklotz': 'Huber AR, Ottiger C, Risch L, Regenass S, Hergersberg M, Herklotz R. Thalassämie-Syndrome: Klinik und Diagnose. Schweiz Mediz Forum. 2004;4:947-52.',
        'kerman_i': 'Cohan N, Ramzi M. Evaluation of sensitivity and specificity of Kerman index I and II in screening beta thalassemia minor. Sci J Iranian Blood Transf Org. 2008;4:297-302.',
        'kerman_ii': 'Cohan N, Ramzi M. Evaluation of sensitivity and specificity of Kerman index I and II in screening beta thalassemia minor. Sci J Iranian Blood Transf Org. 2008;4:297-302.',
        'sirdah': 'Sirdah M, Tarazi I, Al Najjar E, et al. Evaluation of the diagnostic reliability of different RBC indices and formulas in the differentiation of the beta-thalassaemia minor from iron deficiency in Palestinian population. Int J Lab Hematol. 2008;30:324-30.',
        'ehsani': 'Ehsani MA, Shahgholi E, Rahiminejad MS, et al. A new index for discrimination between iron deficiency anemia and beta-thalassemia minor: results in 284 patients. Pakist J Biol Sci. 2009;12:473-5.',
        'keikhaei': 'Keikhaei B. A new valid formula in differentiating iron deficiency anemia from β-thalassemia trait. Pakist J Med Sci. 2010;26:368-73.',
        'nishad': 'Nishad AA, Pathmeswaran A, Wickramasinghe AR, et al. The Thal-index with the BTT prediction.exe to discriminate β-thalassaemia traits from other microcytic anaemias. Thalass Rep. 2012;2:e1-2.',
        'wongprachum': 'Wongprachum K, Sanchaisuriya K, Sanchaisuriya P, et al. Proxy indicators for identifying iron deficiency among anemic vegetarians in an area prevalent for thalassemia and hemoglobinopathies. Acta Haematol. 2012;127:250-5.',
        'sehgal': 'Dharmani P, Sehgal K, Dadu T, Mankeshwar R, Shaikh A, Khodaiji S. Developing a new index and its comparison with other CBC-based indices for screening of beta thalassemia trait in a tertiary care hospital. Int J Lab Hematol. 2013;35:118.',
        'pornprasert': 'Pornprasert S, Panya A, Punyamung M, et al. Red cell indices and formulas used in differentiation of β-thalassemia trait from iron deficiency in Thai school children. Hemoglobin. 2014;38:258-61.',
        'sirachainan': 'Sirachainan N, Iamsirirak P, Charoenkwan P, et al. New mathematical formula for differentiating thalassemia trait and iron deficiency anemia in thalassemia prevalent area: a study in healthy schoolage children. Southeast J Trop Med Publ Health. 2014;45:174-82.',
        'bordbar': 'Bordbar E, Taghipour M, Zucconi BE. Reliability of different RBC indices and formulas in discriminating between beta-thalassemia minor and other microcytic hypochromic cases. Mediterr J Hematol Infect Dis. 2015;7:e2015022.',
        'tidi': 'Pan L, Li L, Qiu Y, et al. A novel discriminant algorithm for differential diagnosis of mild to moderate thalassemia and iron deficiency anemia. Medicine. 2024;103:20(e38205).',
        'df': '尚陈宇. 广州地区地中海贫血基因型分布最新调查及鉴别筛查方程的建立[D]. 广州中医药大学, 2020.',
        'sf': '尚陈宇. 广州地区地中海贫血基因型分布最新调查及鉴别筛查方程的建立[D]. 广州中医药大学, 2020.',
    }

    # 研究人群（Study Populations）
    POPULATIONS = {
        'england_fraser': '英国人群 (British population)',
        'mentzer': '美国人群 (American population)',
        'srivastava': '印度人群 (Indian population)',
        'shine_lal': '英国人群 (British population)',
        'bessman': '美国人群 (American population)',
        'ricerca': '意大利人群 (Italian population)',
        'green_king': '美国人群 (American population)',
        'das_gupta': '印度人群 (Indian population)',
        'rdw_index': '美国儿童人群 (American pediatric population)',
        'mchd': '沙特阿拉伯人群 (Saudi Arabian population)',
        'mdhl': '沙特阿拉伯人群 (Saudi Arabian population)',
        'huber_herklotz': '瑞士人群 (Swiss population)',
        'kerman_i': '伊朗克尔曼地区人群 (Iranian Kerman population)',
        'kerman_ii': '伊朗克尔曼地区人群 (Iranian Kerman population)',
        'sirdah': '巴勒斯坦人群 (Palestinian population)',
        'ehsani': '伊朗人群 (Iranian population)',
        'keikhaei': '伊朗人群 (Iranian population)',
        'nishad': '斯里兰卡人群 (Sri Lankan population)',
        'wongprachum': '泰国素食者人群 (Thai vegetarian population)',
        'sehgal': '印度人群 (Indian population)',
        'pornprasert': '泰国学龄儿童 (Thai school children)',
        'sirachainan': '泰国学龄儿童 (Thai school children)',
        'bordbar': '伊朗人群 (Iranian population)',
        'tidi': '中国广西地区人群 (Chinese Guangxi population)',
        'df': '中国广州地区人群 (Chinese Guangzhou population)',
        'sf': '中国广州地区人群 (Chinese Guangzhou population)',
    }

    # 研究人群详细信息（样本数量和年龄分布）
    POPULATION_DETAILS = {
        'england_fraser': 'N=未详述',
        'mentzer': 'N=未详述',
        'srivastava': 'N=未详述',
        'shine_lal': 'N=未详述',
        'bessman': 'N=未详述',
        'ricerca': 'N=未详述',
        'green_king': 'N=未详述',
        'das_gupta': 'N=未详述',
        'rdw_index': 'N=未详述, 儿童',
        'mchd': 'N=未详述',
        'mdhl': 'N=未详述',
        'huber_herklotz': 'N=未详述',
        'kerman_i': 'N=未详述',
        'kerman_ii': 'N=未详述',
        'sirdah': 'N=380 (β-地贫190, 缺铁190)',
        'ehsani': 'N=284 (β-地贫150, 缺铁134)',
        'keikhaei': 'N=未详述',
        'nishad': 'N=未详述',
        'wongprachum': 'N=393, 成年素食者',
        'sehgal': 'N=未详述',
        'pornprasert': 'N=180, 学龄儿童 (6-15岁)',
        'sirachainan': 'N=456, 学龄儿童 (6-14岁)',
        'bordbar': 'N=300 (β-地贫150, 缺铁150)',
        'tidi': 'N=1863 (地贫1247, 缺铁616), 成人',
        'df': 'N=1200 (广州地区), 成人',
        'sf': 'N=1200 (广州地区), 成人',
    }

    def __init__(self, params: BloodParameters):
        """
        初始化计算器

        Args:
            params: 血液检测参数
        """
        self.params = params

    def _format_calculation(self, formula: str, value: float) -> str:
        """
        根据公式自动生成计算过程字符串

        Args:
            formula: 计算公式（如 "MCV / RBC"）
            value: 计算结果

        Returns:
            带入数值的计算过程字符串
        """
        p = self.params
        process = formula

        # 替换变量为具体数值
        replacements = {
            'MCHC': f'{p.mchc:.2f}',
            'MCH': f'{p.mch}',
            'MCV': f'{p.mcv}',
            'RBC': f'{p.rbc}',
            'RDW': f'{p.rdw}',
            'Hb': f'{p.hb}',
        }

        for var, val in replacements.items():
            process = process.replace(var, val)

        # 添加结果
        process = f"{process} = {value:.2f}"

        return process

    def _create_result(self, key: str, name: str, name_en: str, value: float,
                      threshold: float, operator: str, year: int, formula: str,
                      calculation_process: str = "") -> IndexResult:
        """创建IndexResult对象的辅助方法"""
        rank, ci_value = self.PERFORMANCE_RANK.get(key, (99, 0.0))
        suggests_thalassemia = (value < threshold) if operator == "<" else (value > threshold)

        # 如果没有提供计算过程，自动生成
        if not calculation_process:
            calculation_process = self._format_calculation(formula, value)

        return IndexResult(
            name=name,
            name_en=name_en,
            value=value,
            threshold=threshold,
            operator=operator,
            suggests_thalassemia=suggests_thalassemia,
            reference=self.REFERENCES.get(key, ""),
            year=year,
            ci_value=ci_value,
            rank=rank,
            formula=formula,
            calculation_process=calculation_process,
            population=self.POPULATIONS.get(key, ""),
            population_details=self.POPULATION_DETAILS.get(key, "")
        )

    # ==================== 鉴别诊断公式（序号1-24）====================

    def england_fraser(self) -> IndexResult:
        """1. England & Fraser指数 (E&F)"""
        value = self.params.mcv - self.params.rbc - (5 * self.params.hb) - 3.4
        formula = "MCV - RBC - (5 x Hb) - 3.4"
        return self._create_result('england_fraser', "England & Fraser指数", "England & Fraser (E&F)",
                                  value, 0.0, "<", 1973, formula)

    def mentzer_index(self) -> IndexResult:
        """2. Mentzer指数"""
        value = self.params.mcv / self.params.rbc
        formula = "MCV / RBC"
        return self._create_result('mentzer', "Mentzer指数", "Mentzer Index",
                                  value, 13.0, "<", 1973, formula)

    def srivastava(self) -> IndexResult:
        """3. Srivastava指数"""
        value = self.params.mch / self.params.rbc
        formula = "MCH / RBC"
        return self._create_result('srivastava', "Srivastava指数", "Srivastava Index",
                                  value, 3.8, "<", 1973, formula)

    def shine_lal(self) -> IndexResult:
        """4. Shine & Lal指数 (S&L)"""
        value = (self.params.mcv ** 2) * self.params.mch
        formula = "MCV^2 x MCH"
        return self._create_result('shine_lal', "Shine & Lal指数", "Shine & Lal (S&L)",
                                  value, 1530.0, "<", 1977, formula)

    def bessman(self) -> IndexResult:
        """5. Bessman指数"""
        value = self.params.rdw
        formula = "RDW"
        return self._create_result('bessman', "Bessman指数", "Bessman Index",
                                  value, 15.0, "<", 1979, formula)

    def ricerca(self) -> IndexResult:
        """6. Ricerca指数"""
        value = self.params.rdw / self.params.rbc
        formula = "RDW / RBC"
        return self._create_result('ricerca', "Ricerca指数", "Ricerca Index",
                                  value, 4.4, "<", 1987, formula)

    def green_king(self) -> IndexResult:
        """7. Green & King指数 (G&K)"""
        value = (self.params.mcv ** 2) * self.params.rdw / (self.params.hb * 100)
        formula = "MCV^2 x RDW / (Hb x 100)"
        return self._create_result('green_king', "Green & King指数", "Green & King (G&K)",
                                  value, 65.0, "<", 1989, formula)

    def das_gupta(self) -> IndexResult:
        """8. Das Gupta指数"""
        value = 1.89 * self.params.rbc - 0.33 * self.params.rdw - 3.28
        formula = "1.89 x RBC - 0.33 x RDW - 3.28"
        return self._create_result('das_gupta', "Das Gupta指数", "Das Gupta Index",
                                  value, 0.0, ">", 1994, formula)

    def rdw_index(self) -> IndexResult:
        """9. Jayabose指数 (RDW Index)"""
        value = self.params.mcv * self.params.rdw / self.params.rbc
        formula = "MCV x RDW / RBC"
        return self._create_result('rdw_index', "RDW指数", "RDW Index (Jayabose)",
                                  value, 220.0, "<", 1999, formula)

    def mchd(self) -> IndexResult:
        """10. Telmissani–MCHD"""
        value = self.params.mch / self.params.mcv
        formula = "MCH / MCV"
        return self._create_result('mchd', "MCHD指数", "Telmissani-MCHD",
                                  value, 0.34, "<", 1999, formula)

    def mdhl(self) -> IndexResult:
        """11. Telmissani–MDHL"""
        value = self.params.mch * self.params.rbc / self.params.mcv
        formula = "MCH x RBC / MCV"
        return self._create_result('mdhl', "MDHL指数", "Telmissani-MDHL",
                                  value, 1.75, ">", 1999, formula)

    def huber_herklotz(self) -> IndexResult:
        """12. Huber-Herklotz指数 (H&H)"""
        value = (self.params.mch * self.params.rdw / (10 * self.params.rbc)) + self.params.rdw
        formula = "(MCH x RDW / (10 x RBC)) + RDW"
        return self._create_result('huber_herklotz', "Huber-Herklotz指数", "Huber-Herklotz (H&H)",
                                  value, 20.0, "<", 2004, formula)

    def kerman_i(self) -> IndexResult:
        """13. Kerman I指数"""
        value = self.params.mcv * self.params.mch / self.params.rbc
        formula = "MCV x MCH / RBC"
        return self._create_result('kerman_i', "Kerman I指数", "Kerman I",
                                  value, 300.0, "<", 2008, formula)

    def kerman_ii(self) -> IndexResult:
        """14. Kerman II指数"""
        value = self.params.mcv * self.params.mch * 10 / (self.params.rbc * self.params.mchc)
        formula = "MCV x MCH x 10 / (RBC x MCHC)"
        return self._create_result('kerman_ii', "Kerman II指数", "Kerman II",
                                  value, 85.0, "<", 2008, formula)

    def sirdah(self) -> IndexResult:
        """15. Sirdah指数"""
        value = self.params.mcv - self.params.rbc - (3 * self.params.hb)
        formula = "MCV - RBC - (3 x Hb)"
        # 根据Sirdah 2008年文献：≤ 27 提示β地贫，> 27 提示缺铁性贫血
        return self._create_result('sirdah', "Sirdah指数", "Sirdah Index",
                                  value, 27.0, "<", 2008, formula)

    def ehsani(self) -> IndexResult:
        """16. Ehsani指数"""
        value = self.params.mcv - (10 * self.params.rbc)
        formula = "MCV - (10 x RBC)"
        return self._create_result('ehsani', "Ehsani指数", "Ehsani Index",
                                  value, 15.0, "<", 2009, formula)

    def keikhaei(self) -> IndexResult:
        """17. Keikhaei指数"""
        value = self.params.hb * self.params.rdw * 100 / (self.params.rbc ** 2 * self.params.mchc)
        formula = "Hb x RDW x 100 / (RBC^2 x MCHC)"
        return self._create_result('keikhaei', "Keikhaei指数", "Keikhaei Index",
                                  value, 21.0, "<", 2010, formula)

    def nishad(self) -> IndexResult:
        """18. Nishad指数"""
        value = 0.615 * self.params.mcv + 0.518 * self.params.mch + 0.446 * self.params.rdw
        formula = "0.615 x MCV + 0.518 x MCH + 0.446 x RDW"
        return self._create_result('nishad', "Nishad指数", "Nishad Index",
                                  value, 59.0, "<", 2012, formula)

    def wongprachum(self) -> IndexResult:
        """19. Wongprachum指数"""
        value = (self.params.mcv * self.params.rdw / self.params.rbc) - 10 * self.params.hb
        formula = "(MCV x RDW / RBC) - 10 x Hb"
        return self._create_result('wongprachum', "Wongprachum指数", "Wongprachum Index",
                                  value, 104.0, "<", 2012, formula)

    def sehgal(self) -> IndexResult:
        """20. Sehgal指数"""
        value = (self.params.mcv ** 2) / self.params.rbc
        formula = "MCV^2 / RBC"
        return self._create_result('sehgal', "Sehgal指数", "Sehgal Index",
                                  value, 972.0, "<", 2013, formula)

    def pornprasert(self) -> IndexResult:
        """21. Pornprasert指数"""
        value = self.params.mchc
        formula = "MCHC"
        return self._create_result('pornprasert', "Pornprasert指数", "Pornprasert Index (MCHC)",
                                  value, 31.0, "<", 2014, formula)

    def sirachainan(self) -> IndexResult:
        """22. Sirachainan指数"""
        value = 1.5 * self.params.hb - 0.05 * self.params.mcv
        formula = "1.5 x Hb - 0.05 x MCV"
        # 根据Sirachainan 2014年文献：> 14 提示β地贫，≤ 14 提示缺铁或正常
        return self._create_result('sirachainan', "Sirachainan指数", "Sirachainan Index",
                                  value, 14.0, ">", 2014, formula)

    def bordbar(self) -> IndexResult:
        """23. Bordbar指数"""
        value = abs(80 - self.params.mcv) * abs(27 - self.params.mch)
        formula = "|80 - MCV| x |27 - MCH|"
        return self._create_result('bordbar', "Bordbar指数", "Bordbar Index",
                                  value, 44.76, ">", 2015, formula)

    def df_formula(self) -> IndexResult:
        """24. DF指数（鉴别公式,本研究新建,效能最高）"""
        value = 1.109 * self.params.mch - 0.391 * self.params.mcv + 1.182 * self.params.rbc + 0.116 * self.params.rdw
        formula = "1.109 x MCH - 0.391 x MCV + 1.182 x RBC + 0.116 x RDW"
        return self._create_result('df', "DF指数（鉴别公式）", "DF (Differential Formula)",
                                  value, 4.0877, ">", 2020, formula)

    def tidi_formula(self) -> Optional[IndexResult]:
        """26. TIDI指数（广西地区，含网织红细胞参数）"""
        if self.params.ret_percent is None:
            # 如果没有提供 RET%, 返回 None
            return None

        # 单位转换:
        # - Hb (g/dL -> g/L)
        # - MCHC (g/dL -> % 或 g/L，数值上相等)
        # - RET% 用户输入的是百分比形式（如5表示5%），需要转换为小数形式（0.05）
        hb_gl = self.params.hb * 10  # g/dL -> g/L
        mchc_percent = self.params.mchc * 10  # g/dL -> %
        ret_decimal = self.params.ret_percent / 100  # 百分比 -> 小数 (5% -> 0.05)

        # TIDI = -13.932 + 0.434 × RBC + 0.033 × Hb(g/L) + 0.025 × MCHC(%) + 53.593 × RET%(小数)
        value = (-13.932 +
                 0.434 * self.params.rbc +
                 0.033 * hb_gl +
                 0.025 * mchc_percent +
                 53.593 * ret_decimal)

        formula = "-13.932 + 0.434 x RBC + 0.033 x Hb(g/L) + 0.025 x MCHC(%) + 53.593 x RET%(小数)"

        # 手动生成计算过程，因为涉及单位转换
        calculation = (f"-13.932 + 0.434 x {self.params.rbc} + 0.033 x {hb_gl:.1f} + "
                      f"0.025 x {mchc_percent:.1f} + 53.593 x {ret_decimal:.4f} = {value:.2f}")

        return self._create_result('tidi', "TIDI指数（广西）", "TIDI (Thalassemia and IDA Discrimination Index)",
                                  value, -1.5, "<", 2024, formula, calculation)

    # ==================== 筛查公式（序号25）====================

    def sf_formula(self) -> IndexResult:
        """25. SF指数（筛查公式，用于普通人群筛查）"""
        value = 4.27 * self.params.rbc - 1.309 * self.params.hb + 0.541 * self.params.mch - 0.09 * self.params.mcv + 0.076 * self.params.rdw
        formula = "4.27 x RBC - 1.309 x Hb + 0.541 x MCH - 0.09 x MCV + 0.076 x RDW"
        return self._create_result('sf', "SF指数（筛查公式）", "SF (Screening Formula)",
                                  value, 11.82, ">", 2020, formula)

    def calculate_all(self, sort_by_performance: bool = True) -> List[IndexResult]:
        """
        计算所有指数

        Args:
            sort_by_performance: 是否按效能排序（True=按Ci值排序，False=按序号排序）

        Returns:
            包含所有指数结果的列表
        """
        results = [
            self.england_fraser(),      # 1
            self.mentzer_index(),        # 2
            self.srivastava(),          # 3
            self.shine_lal(),           # 4
            self.bessman(),             # 5
            self.ricerca(),             # 6
            self.green_king(),          # 7
            self.das_gupta(),           # 8
            self.rdw_index(),           # 9
            self.mchd(),                # 10
            self.mdhl(),                # 11
            self.huber_herklotz(),      # 12
            self.kerman_i(),            # 13
            self.kerman_ii(),           # 14
            self.sirdah(),              # 15
            self.ehsani(),              # 16
            self.keikhaei(),            # 17
            self.nishad(),              # 18
            self.wongprachum(),         # 19
            self.sehgal(),              # 20
            self.pornprasert(),         # 21
            self.sirachainan(),         # 22
            self.bordbar(),             # 23
            self.df_formula(),          # 24 - DF鉴别公式
            self.sf_formula(),          # 25 - SF筛查公式
        ]

        # 添加 TIDI (如果提供了 RET%)
        tidi_result = self.tidi_formula()
        if tidi_result is not None:
            results.append(tidi_result)  # 26 - TIDI (需要RET%)

        if sort_by_performance:
            # 按效能排序（Ci值从高到低）
            results.sort(key=lambda x: x.ci_value, reverse=True)

        return results

    def interpret_results(self, results: List[IndexResult]) -> str:
        """
        解释所有结果

        Args:
            results: calculate_all()返回的结果列表

        Returns:
            综合解释文本
        """
        thalassemia_count = sum(1 for r in results if r.suggests_thalassemia)
        total_count = len(results)

        interpretation = f"\n{'='*80}\n"
        interpretation += "综合分析 (Overall Interpretation)\n"
        interpretation += f"{'='*80}\n\n"
        interpretation += f"共有 {thalassemia_count}/{total_count} 个指数提示地中海贫血\n"
        interpretation += f"{thalassemia_count} out of {total_count} indices suggest thalassemia\n\n"

        # 特别关注高效能公式的结果
        top_5_results = [r for r in results if r.rank <= 5]
        top_5_positive = sum(1 for r in top_5_results if r.suggests_thalassemia)

        interpretation += f"高效能公式（Top 5）: {top_5_positive}/5 提示地贫\n"
        interpretation += f"High-performance formulas (Top 5): {top_5_positive}/5 suggest thalassemia\n\n"

        if thalassemia_count >= 20:
            interpretation += "[WARNING] 强烈提示地中海贫血 (Strongly suggests thalassemia)\n"
        elif thalassemia_count >= 15:
            interpretation += "[WARNING] 高度疑似地中海贫血 (Highly suspicious for thalassemia)\n"
        elif thalassemia_count >= 10:
            interpretation += "[WARNING] 提示可能为地中海贫血 (Suggests possible thalassemia)\n"
        elif thalassemia_count >= 5:
            interpretation += "[INFO] 部分指数提示地中海贫血，建议进一步检查 (Some indices suggest thalassemia, further testing recommended)\n"
        else:
            interpretation += "[OK] 多数指数不提示地中海贫血 (Most indices do not suggest thalassemia)\n"

        interpretation += "\n[DISCLAIMER] 免责声明 (Disclaimer):\n"
        interpretation += "本计算器仅供参考，不能替代专业医疗诊断。\n"
        interpretation += "最终诊断必须进行地中海贫血基因检测。\n"
        interpretation += "请咨询专业医生进行确诊。\n\n"
        interpretation += "This calculator is for reference only and cannot replace professional medical diagnosis.\n"
        interpretation += "Final diagnosis must be confirmed by thalassemia genetic testing.\n"
        interpretation += "Please consult a healthcare professional for definitive diagnosis.\n"

        return interpretation


def format_result_table(results: List[IndexResult], show_performance: bool = True) -> str:
    """
    格式化结果为表格

    Args:
        results: 计算结果列表
        show_performance: 是否显示效能信息

    Returns:
        格式化的表格字符串
    """
    if show_performance:
        table = f"\n{'='*150}\n"
        table += f"{'排名':<6} {'指数名称':<22} {'公式':<40} {'计算值':<10} {'阈值':<10} {'结果':<15}\n"
        table += f"{'Rank':<6} {'Index Name':<22} {'Formula':<40} {'Value':<10} {'Threshold':<10} {'Result':<15}\n"
        table += f"{'='*150}\n"

        for result in results:
            result_text = "地贫 (Thal)" if result.suggests_thalassemia else "正常 (Normal)"
            criteria = f"{result.operator}{result.threshold}"
            rank_str = f"#{result.rank}" if result.rank < 99 else "N/A"
            ci_str = f"{result.ci_value:.3f}" if result.ci_value > 0 else "N/A"

            # 缩短公式显示以适应表格
            formula_short = result.formula[:38] + ".." if len(result.formula) > 40 else result.formula

            table += f"{rank_str:<6} {result.name:<20} {formula_short:<40} {result.value:<10.2f} {result.threshold:<10.2f} {result_text:<15}\n"
            table += f"{'':6} {result.name_en:<20} Ci={ci_str} Year={result.year} | Population: {result.population}\n"
            table += f"{'-'*150}\n"
    else:
        table = f"\n{'='*140}\n"
        table += f"{'指数名称':<25} {'公式':<40} {'计算值':<12} {'阈值':<12} {'结果':<20}\n"
        table += f"{'Index Name':<25} {'Formula':<40} {'Value':<12} {'Threshold':<12} {'Result':<20}\n"
        table += f"{'='*140}\n"

        for result in results:
            result_text = "提示地贫 (Thalassemia)" if result.suggests_thalassemia else "正常 (Normal)"
            criteria = f"{result.operator}{result.threshold}"
            formula_short = result.formula[:38] + ".." if len(result.formula) > 40 else result.formula

            table += f"{result.name:<20} {formula_short:<40} {result.value:<12.2f} {result.threshold:<12.2f} {result_text:<20}\n"
            table += f"{result.name_en:<25} | Population: {result.population}\n"
            table += f"{'-'*140}\n"

    return table


if __name__ == "__main__":
    # 示例用法
    print("地中海贫血筛查计算器 (Thalassemia Screening Calculator)")
    print("支持25个筛查公式，按效能排序")
    print("="*80)

    # 示例数据：典型地中海贫血特征
    params = BloodParameters(
        mcv=65.0,   # 低MCV
        rbc=5.5,    # 高RBC
        hb=10.5,    # 低Hb
        mch=18.0,   # 低MCH
        rdw=14.0    # 正常RDW
    )

    # 验证参数
    is_valid, error_msg = params.validate()
    if not is_valid:
        print(f"参数错误: {error_msg}")
    else:
        # 创建计算器并计算
        calculator = ThalassemiaCalculator(params)
        results = calculator.calculate_all(sort_by_performance=True)

        # 显示结果
        print(f"\n输入参数 (Input Parameters):")
        print(f"  MCV: {params.mcv} fL")
        print(f"  RBC: {params.rbc} x10^12/L")
        print(f"  Hb:  {params.hb} g/dL")
        print(f"  MCH: {params.mch} pg")
        print(f"  RDW: {params.rdw} %")
        print(f"  MCHC: {params.mchc:.2f} g/dL (自动计算)")

        print(format_result_table(results, show_performance=True))
        print(calculator.interpret_results(results))

        print(f"\n{'='*80}")
        print("Top 5 高效能公式:")
        print(f"{'='*80}")
        for i, result in enumerate(results[:5], 1):
            status = "[+] 提示地贫" if result.suggests_thalassemia else "[-] 正常"
            print(f"{i}. {result.name} (Ci={result.ci_value:.3f}): {result.value:.2f} {result.operator} {result.threshold} - {status}")
