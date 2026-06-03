"""
数据模型定义
包含消费记录和分类等数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class Category(Enum):
    """消费分类枚举"""
    FOOD = "餐饮"
    TRANSPORT = "交通"
    SHOPPING = "购物"
    ENTERTAINMENT = "娱乐"
    MEDICAL = "医疗"
    COMMUNICATION = "通讯"
    EDUCATION = "教育"
    HOUSING = "居住"
    OTHER = "其他"
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """获取所有分类名称"""
        return [cat.value for cat in cls]


@dataclass
class Record:
    """
    消费记录数据模型
    
    Attributes:
        category: 消费分类
        amount: 消费金额
        date: 消费日期 (YYYY-MM-DD格式)
        description: 消费描述
        note: 备注信息（可选）
        id: 记录唯一标识符
        created_at: 创建时间
    """
    category: Category
    amount: float
    date: str
    description: str
    note: Optional[str] = None
    payment: str = "现金"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def __post_init__(self):
        """数据验证"""
        if self.amount < 0:
            raise ValueError("消费金额不能为负数")
        if not self.date:
            raise ValueError("日期不能为空")
        if not self.description:
            raise ValueError("描述不能为空")
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "category": self.category.value,
            "amount": self.amount,
            "date": self.date,
            "description": self.description,
            "note": self.note,
            "payment": self.payment,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Record":
        """从字典创建记录"""
        category_value = data.get("category", data.get("分类", "其他"))
        category = cls._parse_category(category_value)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            category=category,
            amount=float(data.get("amount", data.get("金额", 0))),
            date=data.get("date", data.get("日期", "")),
            description=data.get("description", data.get("描述", "")),
            note=data.get("note", data.get("备注")),
            payment=data.get("payment", "现金"),
            created_at=data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
    
    @staticmethod
    def _parse_category(value: str) -> Category:
        """解析分类字符串"""
        category_mapping = {
            "餐饮": Category.FOOD,
            "交通": Category.TRANSPORT,
            "购物": Category.SHOPPING,
            "娱乐": Category.ENTERTAINMENT,
            "医疗": Category.MEDICAL,
            "通讯": Category.COMMUNICATION,
            "教育": Category.EDUCATION,
            "居住": Category.HOUSING,
            "其他": Category.OTHER
        }
        
        for key, cat in category_mapping.items():
            if key in value or cat.value in value:
                return cat
        
        return Category.OTHER
    
    def update(self, **kwargs):
        """更新记录字段"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == "category" and isinstance(value, str):
                    value = self._parse_category(value)
                setattr(self, key, value)


@dataclass
class Budget:
    """
    预算数据模型
    
    Attributes:
        monthly_total: 月总预算
        category_limits: 分类预算限额
        start_date: 预算开始日期
        end_date: 预算结束日期
    """
    monthly_total: float = 3000.0
    category_limits: dict = field(default_factory=dict)
    start_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    end_date: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "monthly_total": self.monthly_total,
            "category_limits": self.category_limits,
            "start_date": self.start_date,
            "end_date": self.end_date
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        """从字典创建预算"""
        return cls(
            monthly_total=data.get("monthly_total", 3000.0),
            category_limits=data.get("category_limits", {}),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date")
        )


@dataclass
class UserSettings:
    """
    用户设置数据模型
    
    Attributes:
        currency: 货币符号
        date_format: 日期格式
        theme: 界面主题
        language: 语言
    """
    currency: str = "¥"
    date_format: str = "%Y-%m-%d"
    theme: str = "light"
    language: str = "zh-CN"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "currency": self.currency,
            "date_format": self.date_format,
            "theme": self.theme,
            "language": self.language
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        """从字典创建设置"""
        return cls(
            currency=data.get("currency", "¥"),
            date_format=data.get("date_format", "%Y-%m-%d"),
            theme=data.get("theme", "light"),
            language=data.get("language", "zh-CN")
        )
