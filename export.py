#!/usr/bin/env python3
"""
地中海贫血筛查导出模块
Thalassemia Screening Export Module
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from io import BytesIO

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ExportManager:
    """导出管理类"""
    
    def __init__(self):
        """初始化导出管理器"""
        self.excel_available = EXCEL_AVAILABLE
        self.pdf_available = PDF_AVAILABLE
    
    def export_to_csv(
        self,
        records: List[Dict],
        output_path: str
    ) -> bool:
        """
        导出为CSV格式（包含所有25个指数的详细信息）

        Args:
            records: 筛查记录列表
            output_path: 输出文件路径

        Returns:
            是否导出成功
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                if not records:
                    return False

                # 基本信息列
                basic_fields = [
                    'ID', '患者姓名', '患者ID', '年龄', '性别', '籍贯', '检测日期', '录入日期',
                    'MCV', 'RBC', 'Hb', 'MCH', 'RDW', 'MCHC', 'RET%'
                ]

                # 为每个指数创建多个列（值、结果、公式、效能排名）
                # 我们只包含核心信息以保持CSV可读性
                result_fields = []

                # 从第一条记录获取所有指数名称
                if records:
                    first_results = records[0].get('results', [])
                    if isinstance(first_results, list):
                        # 分离SF和诊断公式，并按效能排序
                        sf_result = None
                        diagnostic_results = []

                        for result in first_results:
                            if result.get('name') == "SF指数（筛查公式）":
                                sf_result = result
                            else:
                                diagnostic_results.append(result)

                        # 诊断公式按效能排序
                        diagnostic_results.sort(key=lambda x: x.get('ci_value', 0), reverse=True)

                        # 组合：先SF，后诊断公式
                        sorted_results = []
                        if sf_result:
                            sorted_results.append(sf_result)
                        sorted_results.extend(diagnostic_results)

                        for result in sorted_results:
                            index_name = result.get('name', '')
                            result_fields.extend([
                                f'{index_name}-值',
                                f'{index_name}-结果',
                                f'{index_name}-排名'
                            ])

                fieldnames = basic_fields + result_fields + ['阳性指数数', '综合结论']

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for record in records:
                    # 基本信息
                    row = {
                        'ID': record.get('id', ''),
                        '患者姓名': record.get('patient_name', ''),
                        '患者ID': record.get('patient_id', ''),
                        '年龄': record.get('age', ''),
                        '性别': record.get('gender', ''),
                        '籍贯': record.get('hometown', ''),
                        '检测日期': record.get('test_date', ''),
                        '录入日期': record.get('screening_date', ''),
                        'MCV': record.get('mcv', ''),
                        'RBC': record.get('rbc', ''),
                        'Hb': record.get('hb', ''),
                        'MCH': record.get('mch', ''),
                        'RDW': record.get('rdw', ''),
                        'MCHC': f"{record.get('mcv', 0) / record.get('rbc', 1) * 100:.2f}" if record.get('rbc') else '',
                        'RET%': record.get('ret_percent', ''),
                    }

                    # 所有指数结果（按SF+诊断公式排序）
                    results = record.get('results', [])
                    if isinstance(results, list):
                        # 分离SF和诊断公式，并按效能排序
                        sf_result = None
                        diagnostic_results = []

                        for result in results:
                            if result.get('name') == "SF指数（筛查公式）":
                                sf_result = result
                            else:
                                diagnostic_results.append(result)

                        # 诊断公式按效能排序
                        diagnostic_results.sort(key=lambda x: x.get('ci_value', 0), reverse=True)

                        # 组合：先SF，后诊断公式
                        sorted_results = []
                        if sf_result:
                            sorted_results.append(sf_result)
                        sorted_results.extend(diagnostic_results)

                        for result in sorted_results:
                            index_name = result.get('name', '')
                            row[f'{index_name}-值'] = f"{result.get('value', 0):.2f}"
                            row[f'{index_name}-结果'] = '阳性' if result.get('suggests_thalassemia') else '阴性'
                            row[f'{index_name}-排名'] = result.get('rank', '')

                    # 综合信息
                    positive_count = record.get('positive_count', 0)
                    total_count = len(results) if isinstance(results, list) else 0
                    row['阳性指数数'] = f"{positive_count}/{total_count}"

                    if positive_count >= 19:
                        row['综合结论'] = '强烈提示地贫'
                    elif positive_count >= 10:
                        row['综合结论'] = '高度疑似地贫'
                    elif positive_count >= 5:
                        row['综合结论'] = '可能地贫'
                    else:
                        row['综合结论'] = '大部分指数正常'

                    writer.writerow(row)

            return True

        except Exception as e:
            print(f"CSV导出错误: {e}")
            return False
    
    def export_to_excel(
        self,
        records: List[Dict],
        output_path: str
    ) -> bool:
        """
        导出为Excel格式（包含所有25个指数的详细信息）

        Args:
            records: 筛查记录列表
            output_path: 输出文件路径

        Returns:
            是否导出成功
        """
        if not self.excel_available:
            raise ImportError("需要安装 openpyxl 库: pip install openpyxl")

        try:
            wb = Workbook()

            # 创建三个工作表：概要信息、详细结果和统计分析
            ws_summary = wb.active
            ws_summary.title = "筛查概要"
            ws_detail = wb.create_sheet("详细结果")
            ws_transpose = wb.create_sheet("统计分析（转置）")

            # 设置样式
            header_font = Font(bold=True, size=11, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            positive_font = Font(color="FF0000", bold=True)
            negative_font = Font(color="27AE60", bold=False)

            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # ========== 概要工作表 ==========
            # 表头
            summary_headers = [
                'ID', '患者姓名', '患者ID', '年龄', '性别', '籍贯', '检测日期',
                'MCV', 'RBC', 'Hb', 'MCH', 'RDW', 'MCHC',
                '阳性数/总数', '阳性率', '综合结论'
            ]

            for col, header in enumerate(summary_headers, 1):
                cell = ws_summary.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border

            # 数据行
            for row_idx, record in enumerate(records, 2):
                positive_count = record.get('positive_count', 0)
                results = record.get('results', [])
                total_count = len(results) if isinstance(results, list) else 0
                positive_rate = f"{positive_count/total_count*100:.1f}%" if total_count > 0 else "N/A"

                if positive_count >= 19:
                    conclusion = '强烈提示地贫'
                elif positive_count >= 10:
                    conclusion = '高度疑似地贫'
                elif positive_count >= 5:
                    conclusion = '可能地贫'
                else:
                    conclusion = '大部分指数正常'

                mchc = record.get('mch', 0) / record.get('mcv', 1) * 100 if record.get('mcv') else 0

                data = [
                    record.get('id', ''),
                    record.get('patient_name', ''),
                    record.get('patient_id', ''),
                    record.get('age', ''),
                    record.get('gender', ''),
                    record.get('hometown', ''),
                    record.get('test_date', record.get('screening_date', '')),
                    record.get('mcv', ''),
                    record.get('rbc', ''),
                    record.get('hb', ''),
                    record.get('mch', ''),
                    record.get('rdw', ''),
                    f"{mchc:.2f}",
                    f"{positive_count}/{total_count}",
                    positive_rate,
                    conclusion
                ]

                for col_idx, value in enumerate(data, 1):
                    cell = ws_summary.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = border
                    cell.alignment = Alignment(horizontal="center", vertical="center")

                    # 根据结论着色
                    if col_idx == len(data):  # 结论列
                        if '强烈' in conclusion or '高度' in conclusion:
                            cell.font = Font(color="FF0000", bold=True)
                        elif '可能' in conclusion:
                            cell.font = Font(color="FF8C00", bold=True)

            # 调整列宽
            column_widths = [8, 12, 12, 6, 6, 12, 18, 8, 8, 8, 8, 8, 8, 12, 10, 15]
            for idx, width in enumerate(column_widths, 1):
                ws_summary.column_dimensions[chr(64 + idx)].width = width

            # ========== 详细结果工作表 ==========
            # 对于每条记录，创建详细的指数信息
            detail_headers = [
                'ID', '患者姓名', '指数序号', '指数名称', '英文名称',
                '公式', '计算过程', '计算值', '阈值', '判断标准',
                '结果', '效能排名', 'Ci值', '年份', '来源人群'
            ]

            for col, header in enumerate(detail_headers, 1):
                cell = ws_detail.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border

            detail_row = 2
            for record in records:
                patient_id = record.get('id', '')
                patient_name = record.get('patient_name', '')
                results = record.get('results', [])

                if isinstance(results, list):
                    # 分离SF筛查公式和诊断公式
                    sf_result = None
                    diagnostic_results = []

                    for result in results:
                        if result.get('name') == "SF指数（筛查公式）":
                            sf_result = result
                        else:
                            diagnostic_results.append(result)

                    # 诊断公式按效能排序
                    diagnostic_results.sort(key=lambda x: x.get('ci_value', 0), reverse=True)

                    # 先添加SF筛查公式
                    if sf_result:
                        suggests_thal = sf_result.get('suggests_thalassemia', False)
                        result_text = '阳性' if suggests_thal else '阴性'

                        detail_data = [
                            patient_id,
                            patient_name,
                            'SF筛查',
                            sf_result.get('name', ''),
                            sf_result.get('name_en', ''),
                            sf_result.get('formula', ''),
                            sf_result.get('calculation_process', ''),
                            f"{sf_result.get('value', 0):.2f}",
                            sf_result.get('threshold', ''),
                            f"{sf_result.get('operator', '')}{sf_result.get('threshold', '')}",
                            result_text,
                            sf_result.get('rank', ''),
                            f"{sf_result.get('ci_value', 0):.3f}",
                            sf_result.get('year', ''),
                            sf_result.get('population', '')
                        ]

                        for col_idx, value in enumerate(detail_data, 1):
                            cell = ws_detail.cell(row=detail_row, column=col_idx, value=value)
                            cell.border = border
                            cell.alignment = Alignment(horizontal="left" if col_idx in [4, 5, 6, 7] else "center",
                                                      vertical="center",
                                                      wrap_text=True if col_idx in [6, 7] else False)
                            # 筛查公式用黄色背景
                            cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")

                            # 结果列着色
                            if col_idx == 11:  # 结果列
                                cell.font = positive_font if suggests_thal else negative_font

                        detail_row += 1

                    # 再添加诊断公式
                    for idx, result in enumerate(diagnostic_results, 1):
                        suggests_thal = result.get('suggests_thalassemia', False)
                        result_text = '阳性' if suggests_thal else '阴性'

                        detail_data = [
                            patient_id,
                            patient_name,
                            idx,
                            result.get('name', ''),
                            result.get('name_en', ''),
                            result.get('formula', ''),
                            result.get('calculation_process', ''),
                            f"{result.get('value', 0):.2f}",
                            result.get('threshold', ''),
                            f"{result.get('operator', '')}{result.get('threshold', '')}",
                            result_text,
                            result.get('rank', ''),
                            f"{result.get('ci_value', 0):.3f}",
                            result.get('year', ''),
                            result.get('population', '')
                        ]

                        for col_idx, value in enumerate(detail_data, 1):
                            cell = ws_detail.cell(row=detail_row, column=col_idx, value=value)
                            cell.border = border
                            cell.alignment = Alignment(horizontal="left" if col_idx in [4, 5, 6, 7] else "center",
                                                      vertical="center",
                                                      wrap_text=True if col_idx in [6, 7] else False)

                            # 结果列着色
                            if col_idx == 11:  # 结果列
                                cell.font = positive_font if suggests_thal else negative_font

                        detail_row += 1

            # 调整详细结果列宽
            detail_widths = [6, 12, 8, 20, 25, 35, 50, 10, 8, 10, 8, 8, 8, 6, 30]
            for idx, width in enumerate(detail_widths, 1):
                ws_detail.column_dimensions[chr(64 + idx)].width = width

            # ========== 统计分析（转置）工作表 ==========
            # 表头行：第一列为"指数名称"，后续列为各条记录
            transpose_headers = ['指数名称']
            for record in records:
                # 使用患者姓名或ID作为列标题
                name = record.get('patient_name', '') or record.get('patient_id', '') or f"记录{record.get('id', '')}"
                transpose_headers.append(name)

            for col, header in enumerate(transpose_headers, 1):
                cell = ws_transpose.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border

            # 数据行：从第一条记录中获取指数列表作为模板
            if records and records[0].get('results'):
                first_results = records[0].get('results', [])
                if isinstance(first_results, list):
                    # 分离SF和诊断公式，并按效能排序
                    sf_result = None
                    diagnostic_results = []

                    for result in first_results:
                        if result.get('name') == "SF指数（筛查公式）":
                            sf_result = result
                        else:
                            diagnostic_results.append(result)

                    # 诊断公式按效能排序
                    diagnostic_results.sort(key=lambda x: x.get('rank', 99))

                    # 组合：先SF，后诊断公式
                    sorted_results = []
                    if sf_result:
                        sorted_results.append(sf_result)
                    sorted_results.extend(diagnostic_results)
                    
                    for row_idx, template_result in enumerate(sorted_results, 2):
                        index_name = template_result.get('name', '')
                        
                        # 第一列：指数名称
                        cell = ws_transpose.cell(row=row_idx, column=1, value=index_name)
                        cell.font = Font(bold=True)
                        cell.border = border
                        cell.alignment = Alignment(horizontal="left", vertical="center")
                        
                        # 后续列：各条记录中该指数的值
                        for col_idx, record in enumerate(records, 2):
                            results = record.get('results', [])
                            value = None
                            suggests_thal = False
                            
                            if isinstance(results, list):
                                # 找到对应的指数
                                for result in results:
                                    if result.get('name') == index_name:
                                        value = result.get('value')
                                        suggests_thal = result.get('suggests_thalassemia', False)
                                        break
                            
                            # 设置单元格值（保持数值类型以便统计）
                            if value is not None:
                                cell = ws_transpose.cell(row=row_idx, column=col_idx, value=float(value))
                                cell.number_format = '0.00'
                                
                                # 设置颜色提示
                                if suggests_thal:
                                    cell.font = Font(color="FF0000", bold=True)  # 阳性：红色加粗
                                else:
                                    cell.font = Font(color="27AE60")  # 阴性：绿色
                            else:
                                cell = ws_transpose.cell(row=row_idx, column=col_idx, value="N/A")
                            
                            cell.border = border
                            cell.alignment = Alignment(horizontal="center", vertical="center")

            # 添加综合信息行
            if records:
                total_results_count = len(sorted_results) if 'sorted_results' in locals() else 25
                summary_row = total_results_count + 3  # 空一行后添加
                
                # 阳性指数数行
                cell = ws_transpose.cell(row=summary_row, column=1, value="阳性指数数")
                cell.font = Font(bold=True, color="FF0000")
                cell.border = border
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
                for col_idx, record in enumerate(records, 2):
                    positive_count = record.get('positive_count', 0)
                    results_count = len(record.get('results', []))
                    cell = ws_transpose.cell(row=summary_row, column=col_idx, 
                                           value=f"{positive_count}/{results_count}")
                    cell.border = border
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = Font(bold=True)
                
                # 综合结论行
                conclusion_row = summary_row + 1
                cell = ws_transpose.cell(row=conclusion_row, column=1, value="综合结论")
                cell.font = Font(bold=True, color="0000FF")
                cell.border = border
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
                for col_idx, record in enumerate(records, 2):
                    positive_count = record.get('positive_count', 0)
                    
                    if positive_count >= 19:
                        conclusion = '强烈提示'
                        font_color = "FF0000"
                    elif positive_count >= 10:
                        conclusion = '高度疑似'
                        font_color = "FF8C00"
                    elif positive_count >= 5:
                        conclusion = '可能地贫'
                        font_color = "FFA500"
                    else:
                        conclusion = '大部分正常'
                        font_color = "27AE60"
                    
                    cell = ws_transpose.cell(row=conclusion_row, column=col_idx, value=conclusion)
                    cell.border = border
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = Font(bold=True, color=font_color)

            # 调整转置表列宽
            ws_transpose.column_dimensions['A'].width = 20  # 指数名称列
            for col_idx in range(2, len(records) + 2):
                col_letter = chr(64 + col_idx)
                ws_transpose.column_dimensions[col_letter].width = 12  # 数据列

            # 冻结首行
            ws_summary.freeze_panes = 'A2'
            ws_detail.freeze_panes = 'A2'
            ws_transpose.freeze_panes = 'B2'  # 冻结第一行和第一列

            # 保存
            wb.save(output_path)
            return True

        except Exception as e:
            print(f"Excel导出错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_to_pdf(
        self,
        record: Dict,
        output_path: str
    ) -> bool:
        """
        导出单条记录为PDF报告（包含所有25个指数的详细信息）

        Args:
            record: 单条筛查记录
            output_path: 输出文件路径

        Returns:
            是否导出成功
        """
        if not self.pdf_available:
            raise ImportError("需要安装 reportlab 库: pip install reportlab")

        try:
            # 注册中文字体
            import os
            import platform

            # 尝试注册系统中文字体
            font_registered = False
            system = platform.system()

            try:
                if system == 'Windows':
                    # Windows系统字体路径
                    font_paths = [
                        'C:/Windows/Fonts/msyh.ttc',  # 微软雅黑
                        'C:/Windows/Fonts/simhei.ttf',  # 黑体
                        'C:/Windows/Fonts/simsun.ttc',  # 宋体
                    ]
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            if font_path.endswith('.ttc'):
                                # TTC文件需要指定subfontIndex
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                            else:
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_registered = True
                            break
                elif system == 'Darwin':  # macOS
                    font_paths = [
                        '/System/Library/Fonts/PingFang.ttc',
                        '/Library/Fonts/Arial Unicode.ttf',
                    ]
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            if font_path.endswith('.ttc'):
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                            else:
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_registered = True
                            break
                else:  # Linux
                    font_paths = [
                        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                    ]
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            if font_path.endswith('.ttc'):
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                            else:
                                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_registered = True
                            break
            except Exception as e:
                print(f"字体注册警告: {e}")

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch,
                leftMargin=0.5*inch,
                rightMargin=0.5*inch
            )
            story = []
            styles = getSampleStyleSheet()

            # 标题
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=20,
                alignment=1,  # 居中
                fontName='ChineseFont' if font_registered else 'Helvetica-Bold'
            )

            story.append(Paragraph("地中海贫血筛查报告", title_style))
            story.append(Paragraph("Thalassemia Screening Report", title_style))
            story.append(Spacer(1, 0.2*inch))

            # 患者信息
            patient_data = [
                ['患者信息 (Patient Information)', ''],
                ['姓名 (Name):', record.get('patient_name', 'N/A')],
                ['患者ID (Patient ID):', record.get('patient_id', 'N/A')],
                ['年龄 (Age):', str(record.get('age', 'N/A'))],
                ['性别 (Gender):', record.get('gender', 'N/A')],
                ['籍贯 (Hometown):', record.get('hometown', 'N/A')],
                ['检测日期 (Test Date):', record.get('test_date', record.get('screening_date', 'N/A'))]
            ]

            patient_table = Table(patient_data, colWidths=[3*inch, 3.5*inch])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(patient_table)
            story.append(Spacer(1, 0.15*inch))

            # 血液参数
            mchc = record.get('mch', 0) / record.get('mcv', 1) * 100 if record.get('mcv') else 0
            blood_data = [
                ['血液检测参数 (Blood Parameters)', '数值 (Value)', '单位 (Unit)'],
                ['MCV - 平均红细胞体积', f"{record.get('mcv', 'N/A')}", 'fL'],
                ['RBC - 红细胞计数', f"{record.get('rbc', 'N/A')}", 'x10^12/L'],
                ['Hb - 血红蛋白', f"{record.get('hb', 'N/A')}", 'g/dL'],
                ['MCH - 平均红细胞血红蛋白', f"{record.get('mch', 'N/A')}", 'pg'],
                ['RDW - 红细胞分布宽度', f"{record.get('rdw', 'N/A')}", '%'],
                ['MCHC - 平均红细胞血红蛋白浓度', f"{mchc:.2f}", 'g/dL']
            ]

            blood_table = Table(blood_data, colWidths=[3*inch, 2*inch, 1.5*inch])
            blood_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(blood_table)
            story.append(Spacer(1, 0.15*inch))

            # 综合结论（放在前面）
            positive_count = record.get('positive_count', 0)
            results = record.get('results', [])
            total_count = len(results) if isinstance(results, list) else 0

            conclusion_text = f"<b>筛查结果概要 (Screening Summary):</b><br/>"
            conclusion_text += f"阳性指数: {positive_count}/{total_count} | Positive Indices: {positive_count}/{total_count}<br/>"

            if positive_count >= 19:
                conclusion_text += '<font color="red"><b>结论: 强烈提示地中海贫血 (Strongly suggests thalassemia)</b></font><br/>'
            elif positive_count >= 10:
                conclusion_text += '<font color="orangered"><b>结论: 高度疑似地中海贫血 (Highly suspicious for thalassemia)</b></font><br/>'
            elif positive_count >= 5:
                conclusion_text += '<font color="orange"><b>结论: 提示可能为地中海贫血 (Suggests possible thalassemia)</b></font><br/>'
            else:
                conclusion_text += '<font color="green"><b>结论: 大部分指数正常 (Most indices are normal)</b></font><br/>'

            # 创建中文段落样式
            chinese_style = ParagraphStyle(
                'ChineseNormal',
                parent=styles['Normal'],
                fontName='ChineseFont' if font_registered else 'Helvetica',
                fontSize=10
            )
            story.append(Paragraph(conclusion_text, chinese_style))
            story.append(Spacer(1, 0.15*inch))

            # 计算结果 - 详细表格（分页显示）
            heading_style = ParagraphStyle(
                'ChineseHeading',
                parent=styles['Heading2'],
                fontName='ChineseFont' if font_registered else 'Helvetica-Bold',
                fontSize=12
            )

            if isinstance(results, list) and len(results) > 0:
                # 分离SF筛查公式和诊断公式
                sf_result = None
                diagnostic_results = []

                for result in results:
                    if result.get('name') == "SF指数（筛查公式）":
                        sf_result = result
                    else:
                        diagnostic_results.append(result)

                # 诊断公式按效能排序
                diagnostic_results.sort(key=lambda x: x.get('ci_value', 0), reverse=True)

                # 第一部分：SF筛查公式（如果存在）
                if sf_result:
                    story.append(Paragraph("<b>筛查公式 (Screening Formula)</b>", heading_style))

                    sf_data = [['类型', '指数', '公式', '值', '判断', '结果', 'Ci值']]

                    suggests_thal = sf_result.get('suggests_thalassemia', False)
                    result_text = '阳性' if suggests_thal else '阴性'
                    criteria = f"{sf_result.get('operator', '')}{sf_result.get('threshold', '')}"

                    formula_style_sf = ParagraphStyle(
                        'SFFormulaStyle',
                        parent=styles['Normal'],
                        fontName='ChineseFont' if font_registered else 'Helvetica',
                        fontSize=6,
                        leading=7,
                        alignment=0
                    )

                    formula = sf_result.get('formula', '')
                    formula_para = Paragraph(formula, formula_style_sf)

                    sf_data.append([
                        '筛查',
                        sf_result.get('name', '')[:15],
                        formula_para,
                        f"{sf_result.get('value', 0):.2f}",
                        criteria,
                        result_text,
                        f"{sf_result.get('ci_value', 0):.3f}"
                    ])

                    sf_table = Table(sf_data, colWidths=[0.5*inch, 1.1*inch, 2.2*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.6*inch])
                    sf_table_style = [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if font_registered else 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, 0), 8),
                        ('FONTSIZE', (0, 1), (-1, -1), 7),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                        ('TOPPADDING', (0, 1), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                    ]

                    if sf_result.get('suggests_thalassemia'):
                        sf_table_style.append(('TEXTCOLOR', (5, 1), (5, 1), colors.red))

                    sf_table.setStyle(TableStyle(sf_table_style))
                    story.append(sf_table)
                    story.append(Spacer(1, 0.15*inch))

                # 第二部分：Top 10 诊断公式
                story.append(Paragraph("<b>Top 10 诊断公式 (Top 10 Diagnostic Formulas)</b>", heading_style))

                top10_data = [['序号', '指数', '公式', '值', '判断', '结果', 'Ci值']]

                # 创建小字体样式用于Top 10表格的公式
                top10_formula_style = ParagraphStyle(
                    'Top10FormulaStyle',
                    parent=styles['Normal'],
                    fontName='ChineseFont' if font_registered else 'Helvetica',
                    fontSize=6,
                    leading=7,
                    alignment=0  # 左对齐
                )

                for idx, result in enumerate(diagnostic_results[:10], 1):
                    suggests_thal = result.get('suggests_thalassemia', False)
                    result_text = '阳性' if suggests_thal else '阴性'
                    criteria = f"{result.get('operator', '')}{result.get('threshold', '')}"

                    # 使用Paragraph包装公式以支持自动换行
                    formula = result.get('formula', '')
                    formula_para = Paragraph(formula, top10_formula_style)

                    top10_data.append([
                        f"#{idx}",
                        result.get('name', '')[:15],
                        formula_para,  # 使用Paragraph对象，不再截断
                        f"{result.get('value', 0):.2f}",
                        criteria,
                        result_text,
                        f"{result.get('ci_value', 0):.3f}"
                    ])

                top10_table = Table(top10_data, colWidths=[0.4*inch, 1.1*inch, 2.3*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.6*inch])
                table_style = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if font_registered else 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TOPPADDING', (0, 1), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    # 公式列左对齐
                    ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ]

                # 为阳性结果着色
                for row_idx, result in enumerate(diagnostic_results[:10], 1):
                    if result.get('suggests_thalassemia'):
                        table_style.append(('TEXTCOLOR', (5, row_idx), (5, row_idx), colors.red))

                top10_table.setStyle(TableStyle(table_style))
                story.append(top10_table)
                story.append(PageBreak())

                # 第二页：所有指数详细信息
                story.append(Paragraph("<b>所有诊断公式详细结果 (All Diagnostic Formulas Detailed Results)</b>", heading_style))
                story.append(Spacer(1, 0.1*inch))

                # 由于PDF空间限制，将结果分为几个部分
                batch_size = 6  # 减少每批数量以适应新列

                # 创建小字体样式用于公式
                formula_style = ParagraphStyle(
                    'FormulaStyle',
                    parent=styles['Normal'],
                    fontName='ChineseFont' if font_registered else 'Helvetica',
                    fontSize=6.5,
                    leading=8,
                    alignment=0  # 左对齐
                )

                # 创建小字体样式用于指数名称
                name_style = ParagraphStyle(
                    'NameStyle',
                    parent=styles['Normal'],
                    fontName='ChineseFont' if font_registered else 'Helvetica',
                    fontSize=6.5,
                    leading=8,
                    alignment=1  # 居中
                )

                # 创建小字体样式用于人群信息
                population_style = ParagraphStyle(
                    'PopulationStyle',
                    parent=styles['Normal'],
                    fontName='ChineseFont' if font_registered else 'Helvetica',
                    fontSize=6,
                    leading=7,
                    alignment=1  # 居中
                )

                # 只处理诊断公式，不包括SF
                for batch_start in range(0, len(diagnostic_results), batch_size):
                    batch_results = diagnostic_results[batch_start:batch_start + batch_size]

                    detail_data = [['#', '指数', '公式', '值', '标准', '结果', '来源人群']]

                    for idx, result in enumerate(batch_results, batch_start + 1):
                        suggests_thal = result.get('suggests_thalassemia', False)
                        result_text = '阳性' if suggests_thal else '阴性'
                        criteria = f"{result.get('operator', '')}{result.get('threshold', '')}"
                        # 使用Paragraph包装公式以支持自动换行
                        formula = result.get('formula', '')
                        formula_para = Paragraph(formula, formula_style)
                        # 使用Paragraph包装指数名称以支持自动换行
                        name = result.get('name', '')
                        name_para = Paragraph(name, name_style)
                        # 使用Paragraph包装人群信息以支持自动换行（只显示中文部分）
                        population = result.get('population', '')
                        if '(' in population:
                            population = population.split('(')[0].strip()
                        population_para = Paragraph(population, population_style)

                        detail_data.append([
                            str(idx),
                            name_para,  # 使用Paragraph对象，不再截断
                            formula_para,  # 使用Paragraph对象
                            f"{result.get('value', 0):.2f}",
                            criteria,
                            result_text,
                            population_para  # 使用Paragraph对象，完整显示
                        ])

                    # 调整列宽，给人群列适当空间
                    detail_table = Table(detail_data, colWidths=[0.25*inch, 1.05*inch, 2.2*inch, 0.5*inch, 0.5*inch, 0.45*inch, 0.9*inch])
                    detail_style = [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if font_registered else 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, 0), 7),
                        ('FONTSIZE', (0, 1), (-1, -1), 6.5),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                        ('TOPPADDING', (0, 1), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        # 公式列左对齐
                        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                    ]

                    # 为阳性结果着色
                    for row_idx, result in enumerate(batch_results, 1):
                        if result.get('suggests_thalassemia'):
                            detail_style.append(('TEXTCOLOR', (5, row_idx), (5, row_idx), colors.red))

                    detail_table.setStyle(TableStyle(detail_style))
                    story.append(detail_table)
                    story.append(Spacer(1, 0.1*inch))

            # 免责声明
            story.append(Spacer(1, 0.2*inch))
            disclaimer = """
            <b>免责声明 (Disclaimer):</b><br/>
            本报告仅供参考，不能替代专业医疗诊断。地中海贫血的最终诊断必须通过基因检测确认。
            请咨询专业医生进行确诊。<br/>
            <i>This report is for reference only and cannot replace professional medical diagnosis.
            Final diagnosis of thalassemia must be confirmed by genetic testing.
            Please consult a healthcare professional for definitive diagnosis.</i>
            """
            disclaimer_style = ParagraphStyle(
                'ChineseDisclaimer',
                parent=styles['Normal'],
                fontName='ChineseFont' if font_registered else 'Helvetica',
                fontSize=9
            )
            story.append(Paragraph(disclaimer, disclaimer_style))

            # 生成PDF
            doc.build(story)
            return True

        except Exception as e:
            print(f"PDF导出错误: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _format_result(self, result: Optional[Dict]) -> str:
        """格式化结果为字符串"""
        if not result:
            return ''
        
        value = result.get('value', 0)
        suggests = result.get('suggests_thalassemia', False)
        return f"{value:.2f} ({'阳性' if suggests else '阴性'})"
    
    def _get_result_value(self, result: Optional[Dict]) -> str:
        """获取结果值"""
        if not result:
            return ''
        return f"{result.get('value', 0):.2f}"


if __name__ == "__main__":
    # 测试导出功能
    print("测试导出模块...")
    
    # 创建测试数据
    test_record = {
        'id': 1,
        'patient_name': '测试患者',
        'patient_id': 'TEST001',
        'age': 30,
        'gender': '男',
        'screening_date': '2025-11-27 10:00:00',
        'mcv': 65.0,
        'rbc': 5.5,
        'hb': 10.5,
        'mch': 18.0,
        'rdw': 14.0,
        'positive_count': 5,
        'results': {
            'mentzer': {'name': 'Mentzer指数', 'value': 11.82, 'threshold': 13.0, 'operator': '<', 'suggests_thalassemia': True},
            'england_fraser': {'name': 'England & Fraser', 'value': -5.4, 'threshold': 0.0, 'operator': '<', 'suggests_thalassemia': True}
        }
    }
    
    exporter = ExportManager()
    
    # 测试CSV导出
    if exporter.export_to_csv([test_record], 'test_export.csv'):
        print("✓ CSV导出成功")
    
    # 测试Excel导出
    if EXCEL_AVAILABLE:
        if exporter.export_to_excel([test_record], 'test_export.xlsx'):
            print("✓ Excel导出成功")
    else:
        print("⚠ Excel导出不可用 (需要安装 openpyxl)")
    
    # 测试PDF导出
    if PDF_AVAILABLE:
        if exporter.export_to_pdf(test_record, 'test_export.pdf'):
            print("✓ PDF导出成功")
    else:
        print("⚠ PDF导出不可用 (需要安装 reportlab)")
    
    print("\n导出模块测试完成！")
