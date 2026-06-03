"""
数据存储模块
负责数据的持久化存储和读取
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import shutil

from models import Record, Budget, UserSettings, Category


class DataStorage:
    """
    数据存储类
    负责消费记录的增删改查和文件持久化
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化数据存储
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "records.json"
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.records: List[Record] = []
        self.budget = Budget()
        self.settings = UserSettings()
        
        self._load_data()
    
    def _load_data(self):
        """从文件加载数据"""
        if not self.data_file.exists():
            self.records = []
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"数据文件格式错误: {e}")
            self.records = []
            return
        except Exception as e:
            print(f"读取数据文件时发生错误: {e}")
            self.records = []
            return
        
        try:
            # 加载消费记录
            records_data = data.get('records', [])
            self.records = [Record.from_dict(r) for r in records_data]
            
            # 加载预算设置
            budget_data = data.get('budget')
            if budget_data:
                self.budget = Budget.from_dict(budget_data)
            
            # 加载用户设置
            settings_data = data.get('settings')
            if settings_data:
                self.settings = UserSettings.from_dict(settings_data)
        except Exception as e:
            print(f"解析数据时发生错误: {e}")
            self.records = []
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            data = {
                'records': [r.to_dict() for r in self.records],
                'budget': self.budget.to_dict(),
                'settings': self.settings.to_dict(),
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise IOError(f"保存数据失败: {e}")
    
    def load_data(self):
        """重新加载数据"""
        self._load_data()
    
    def add_record(self, record: Record) -> bool:
        """
        添加消费记录
        
        Args:
            record: 消费记录对象
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 验证数据
            if not isinstance(record, Record):
                raise ValueError("无效的记录对象")
            
            if record.amount <= 0:
                raise ValueError("金额必须大于0")
            
            self.records.append(record)
            self._save_data()
            return True
        except Exception as e:
            print(f"添加记录失败: {e}")
            return False
    
    def update_record(self, record_id: str, **kwargs) -> bool:
        """
        更新消费记录
        
        Args:
            record_id: 记录ID
            **kwargs: 要更新的字段
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for record in self.records:
                if record.id == record_id:
                    record.update(**kwargs)
                    self._save_data()
                    return True
            return False
        except Exception as e:
            print(f"更新记录失败: {e}")
            return False
    
    def delete_record(self, record_id: str) -> bool:
        """
        删除消费记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            initial_length = len(self.records)
            self.records = [r for r in self.records if r.id != record_id]
            
            if len(self.records) < initial_length:
                self._save_data()
                return True
            return False
        except Exception as e:
            print(f"删除记录失败: {e}")
            return False
    
    def get_record(self, record_id: str) -> Optional[Record]:
        """
        获取指定记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            Record: 记录对象，未找到返回None
        """
        for record in self.records:
            if record.id == record_id:
                return record
        return None
    
    def get_all_records(self) -> List[Record]:
        """
        获取所有记录
        
        Returns:
            List[Record]: 所有消费记录列表
        """
        return self.records.copy()
    
    def get_records_by_category(self, category: str) -> List[Record]:
        """
        按分类筛选记录
        
        Args:
            category: 分类名称
            
        Returns:
            List[Record]: 该分类的所有记录
        """
        return [r for r in self.records if r.category.value == category]
    
    def get_records_by_date_range(self, start_date: str, end_date: str) -> List[Record]:
        """
        按日期范围筛选记录
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            List[Record]: 日期范围内的记录
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            return [
                r for r in self.records
                if start <= datetime.strptime(r.date, "%Y-%m-%d") <= end
            ]
        except ValueError as e:
            print(f"日期格式错误: {e}")
            return []
    
    def search_records(self, keyword: str) -> List[Record]:
        """
        搜索记录
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Record]: 匹配的记录
        """
        keyword = keyword.lower()
        return [
            r for r in self.records
            if keyword in r.description.lower()
            or keyword in (r.note or "").lower()
            or keyword in r.category.value.lower()
        ]
    
    def clear_all(self) -> bool:
        """
        清空所有记录
        
        Returns:
            bool: 是否清空成功
        """
        try:
            self.records = []
            self._save_data()
            return True
        except Exception as e:
            print(f"清空数据失败: {e}")
            return False
    
    def update_budget(self, budget: Budget) -> bool:
        """
        更新预算设置
        
        Args:
            budget: 预算对象
            
        Returns:
            bool: 是否更新成功
        """
        try:
            self.budget = budget
            self._save_data()
            return True
        except Exception as e:
            print(f"更新预算失败: {e}")
            return False
    
    def update_settings(self, settings: UserSettings) -> bool:
        """
        更新用户设置
        
        Args:
            settings: 设置对象
            
        Returns:
            bool: 是否更新成功
        """
        try:
            self.settings = settings
            self._save_data()
            return True
        except Exception as e:
            print(f"更新设置失败: {e}")
            return False
    
    def create_backup(self) -> str:
        """
        创建数据备份
        
        Returns:
            str: 备份文件路径
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"backup_{timestamp}.json"
            
            shutil.copy2(self.data_file, backup_file)
            return str(backup_file)
        except Exception as e:
            print(f"创建备份失败: {e}")
            return ""
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        恢复备份
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 是否恢复成功
        """
        try:
            backup_path_obj = Path(backup_path)
            if not backup_path_obj.exists():
                print(f"备份文件不存在: {backup_path}")
                return False
            if not backup_path_obj.suffix == '.json':
                print(f"备份文件格式错误: {backup_path}")
                return False
            shutil.copy2(backup_path, self.data_file)
            self._load_data()
            return True
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False

    def read_backup_file(self, backup_path: str) -> list:
        """
        读取备份文件内容（不恢复）

        Args:
            backup_path: 备份文件路径

        Returns:
            list: Record 对象列表
        """
        import json
        records = []
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("records", []):
            try:
                cat = Category(item.get("category", "其他"))
                records.append(Record(
                    id=item.get("id"),
                    amount=float(item.get("amount", 0)),
                    category=cat,
                    description=item.get("description", ""),
                    date=item.get("date", ""),
                    payment=item.get("payment", item.get("payment_method", "现金"))
                ))
            except Exception:
                continue
        return records

    def delete_backup_file(self, backup_path: str) -> bool:
        """
        删除备份文件

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 是否删除成功
        """
        import os
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                return True
            return False
        except Exception:
            return False

    def get_statistics(self) -> dict:
        """
        获取统计信息
        
        Returns:
            dict: 统计数据字典
        """
        if not self.records:
            return {
                "total": 0,
                "count": 0,
                "avg": 0,
                "max": 0,
                "min": 0,
                "categories": {}
            }
        
        amounts = [r.amount for r in self.records]
        categories = {}
        
        for r in self.records:
            cat_name = r.category.value
            categories[cat_name] = categories.get(cat_name, 0) + r.amount
        
        return {
            "total": sum(amounts),
            "count": len(amounts),
            "avg": sum(amounts) / len(amounts) if amounts else 0,
            "max": max(amounts) if amounts else 0,
            "min": min(amounts) if amounts else 0,
            "categories": categories
        }
