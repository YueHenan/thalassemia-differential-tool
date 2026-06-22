#!/usr/bin/env python3
"""
地中海贫血筛查数据库管理模块
Thalassemia Screening Database Management Module
"""

import sqlite3
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import asdict
from thalassemia_calculator import BloodParameters, IndexResult


def get_app_path(relative_path: str = "") -> str:
    """
    获取应用程序目录的绝对路径
    
    在打包为exe后，使用sys.executable获取exe所在目录
    在开发环境中，使用脚本所在目录
    
    Args:
        relative_path: 相对于应用目录的路径
        
    Returns:
        绝对路径
    """
    # 检测是否为打包的exe
    if getattr(sys, 'frozen', False):
        # 打包后，使用exe所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 开发环境，使用脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


class ScreeningDatabase:
    """地中海贫血筛查数据库管理类"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径（应用程序目录下的data/thalassemia.db）
        """
        if db_path is None:
            # 使用应用程序目录下的data文件夹
            db_path = get_app_path("data/thalassemia.db")
        
        self.db_path = db_path
        
        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建筛查记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screening_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT,
                patient_id TEXT,
                age INTEGER,
                gender TEXT,
                hometown TEXT,
                test_date DATE,
                screening_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mcv REAL NOT NULL,
                rbc REAL NOT NULL,
                hb REAL NOT NULL,
                mch REAL NOT NULL,
                rdw REAL NOT NULL,
                results_json TEXT NOT NULL,
                positive_count INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 检查并添加test_date列（如果不存在）- 数据库迁移
        cursor.execute("PRAGMA table_info(screening_records)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'test_date' not in columns:
            print("正在添加 test_date 列到现有数据库...")
            cursor.execute('ALTER TABLE screening_records ADD COLUMN test_date DATE')
            # 将现有记录的screening_date复制到test_date
            cursor.execute('UPDATE screening_records SET test_date = DATE(screening_date) WHERE test_date IS NULL')
            conn.commit()
            print("[OK] 数据库迁移完成")

        # 检查并添加hometown列（如果不存在）- 数据库迁移
        if 'hometown' not in columns:
            print("正在添加 hometown 列到现有数据库...")
            cursor.execute('ALTER TABLE screening_records ADD COLUMN hometown TEXT')
            conn.commit()
            print("[OK] hometown列添加完成")

        # 创建索引以提高查询性能
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_test_date
            ON screening_records(test_date)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_screening_date
            ON screening_records(screening_date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_patient_id 
            ON screening_records(patient_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_screening(
        self,
        params: BloodParameters,
        results: List[IndexResult],
        patient_name: str = "",
        patient_id: str = "",
        age: Optional[int] = None,
        gender: str = "",
        hometown: str = "",
        test_date: Optional[str] = None,
        notes: str = ""
    ) -> int:
        """
        保存筛查记录

        Args:
            params: 血液检测参数
            results: 计算结果列表（已按效能排序）
            patient_name: 患者姓名
            patient_id: 患者ID/病历号
            age: 年龄
            gender: 性别
            hometown: 籍贯
            test_date: 血液检测日期 (YYYY-MM-DD)，如果不提供则使用当前日期
            notes: 备注

        Returns:
            记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 如果没有提供检测日期，使用当前日期
        if not test_date:
            from datetime import datetime
            test_date = datetime.now().strftime('%Y-%m-%d')

        # 将结果列表转换为JSON格式存储
        results_list = []
        for result in results:
            results_list.append({
                'name': result.name,
                'name_en': result.name_en,
                'value': result.value,
                'threshold': result.threshold,
                'operator': result.operator,
                'suggests_thalassemia': result.suggests_thalassemia,
                'reference': result.reference,
                'year': result.year,
                'ci_value': result.ci_value,
                'rank': result.rank,
                'formula': result.formula,
                'calculation_process': result.calculation_process,
                'population': result.population
            })

        results_json = json.dumps(results_list, ensure_ascii=False)

        # 计算阳性指数数量
        positive_count = sum(1 for r in results if r.suggests_thalassemia)
        
        cursor.execute('''
            INSERT INTO screening_records
            (patient_name, patient_id, age, gender, hometown, test_date, mcv, rbc, hb, mch, rdw,
             results_json, positive_count, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_name, patient_id, age, gender, hometown, test_date,
            params.mcv, params.rbc, params.hb, params.mch, params.rdw,
            results_json, positive_count, notes
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_all_records(self, limit: Optional[int] = None) -> List[Dict]:
        """
        获取所有筛查记录
        
        Args:
            limit: 限制返回记录数量
            
        Returns:
            记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM screening_records 
            ORDER BY screening_date DESC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            record = dict(row)
            # 解析JSON结果
            record['results'] = json.loads(record['results_json'])
            del record['results_json']
            records.append(record)
        
        conn.close()
        return records
    
    def get_record_by_id(self, record_id: int) -> Optional[Dict]:
        """
        根据ID获取记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录字典，如果不存在返回None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM screening_records WHERE id = ?',
            (record_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            record = dict(row)
            record['results'] = json.loads(record['results_json'])
            del record['results_json']
            return record
        
        return None
    
    def get_records_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        按日期范围查询记录
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM screening_records 
            WHERE DATE(screening_date) BETWEEN ? AND ?
            ORDER BY screening_date DESC
        ''', (start_date, end_date))
        
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            record = dict(row)
            record['results'] = json.loads(record['results_json'])
            del record['results_json']
            records.append(record)
        
        conn.close()
        return records
    
    def get_patient_history(self, patient_id: str) -> List[Dict]:
        """
        获取患者历史记录
        
        Args:
            patient_id: 患者ID
            
        Returns:
            该患者的所有记录
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM screening_records 
            WHERE patient_id = ?
            ORDER BY screening_date DESC
        ''', (patient_id,))
        
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            record = dict(row)
            record['results'] = json.loads(record['results_json'])
            del record['results_json']
            records.append(record)
        
        conn.close()
        return records
    
    def search_records(
        self,
        keyword: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_positive: Optional[int] = None
    ) -> List[Dict]:
        """
        搜索记录
        
        Args:
            keyword: 关键词（搜索姓名、患者ID）
            start_date: 开始日期
            end_date: 结束日期
            min_positive: 最小阳性指数数量
            
        Returns:
            符合条件的记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM screening_records WHERE 1=1'
        params = []
        
        if keyword:
            query += ' AND (patient_name LIKE ? OR patient_id LIKE ?)'
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        
        if start_date:
            query += ' AND DATE(screening_date) >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND DATE(screening_date) <= ?'
            params.append(end_date)
        
        if min_positive is not None:
            query += ' AND positive_count >= ?'
            params.append(min_positive)
        
        query += ' ORDER BY screening_date DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            record = dict(row)
            record['results'] = json.loads(record['results_json'])
            del record['results_json']
            records.append(record)
        
        conn.close()
        return records
    
    def delete_record(self, record_id: int) -> bool:
        """
        删除记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'DELETE FROM screening_records WHERE id = ?',
            (record_id,)
        )
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_statistics(self) -> Dict:
        """
        获取基本统计信息
        
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) FROM screening_records')
        total_records = cursor.fetchone()[0]
        
        # 阳性记录数（至少3个指数阳性）
        cursor.execute(
            'SELECT COUNT(*) FROM screening_records WHERE positive_count >= 3'
        )
        positive_records = cursor.fetchone()[0]
        
        # 平均阳性指数数量
        cursor.execute('SELECT AVG(positive_count) FROM screening_records')
        avg_positive = cursor.fetchone()[0] or 0
        
        # 最早和最晚记录日期
        cursor.execute(
            'SELECT MIN(screening_date), MAX(screening_date) FROM screening_records'
        )
        date_range = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_records': total_records,
            'positive_records': positive_records,
            'positive_rate': positive_records / total_records if total_records > 0 else 0,
            'avg_positive_count': avg_positive,
            'earliest_date': date_range[0],
            'latest_date': date_range[1]
        }


if __name__ == "__main__":
    # 测试数据库功能
    from thalassemia_calculator import ThalassemiaCalculator
    
    print("测试数据库模块...")
    
    # 创建数据库实例
    db = ScreeningDatabase()
    
    # 创建测试数据
    params = BloodParameters(
        mcv=65.0,
        rbc=5.5,
        hb=10.5,
        mch=18.0,
        rdw=14.0
    )
    
    calculator = ThalassemiaCalculator(params)
    results = calculator.calculate_all()
    
    # 保存记录
    record_id = db.save_screening(
        params=params,
        results=results,
        patient_name="测试患者",
        patient_id="TEST001",
        age=30,
        gender="男",
        notes="测试记录"
    )
    
    print(f"✓ 保存记录成功，ID: {record_id}")
    
    # 获取记录
    record = db.get_record_by_id(record_id)
    print(f"✓ 获取记录成功: {record['patient_name']}")
    
    # 获取统计信息
    stats = db.get_statistics()
    print(f"✓ 统计信息: 总记录数 {stats['total_records']}, 阳性率 {stats['positive_rate']:.2%}")
    
    print("\n数据库模块测试完成！")
