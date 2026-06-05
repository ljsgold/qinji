"""
工具函数模块
包含格式化、验证、统计等辅助函数
"""

import os
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from models import Record, Category


def format_currency(amount: float, currency: str = "¥") -> str:
    """
    格式化货币金额
    
    Args:
        amount: 金额
        currency: 货币符号
        
    Returns:
        str: 格式化后的字符串
    """
    return f"{currency}{amount:,.2f}"


def get_date_range_options() -> Dict[str, Tuple[str, str]]:
    """
    获取日期范围选项
    
    Returns:
        Dict: 日期范围选项字典
    """
    today = datetime.now()
    
    return {
        "今天": (
            today.strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ),
        "本周": (
            (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ),
        "本月": (
            today.replace(day=1).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ),
        "本季度": (
            today.replace(month=(today.month - 1) // 3 * 3 + 1, day=1).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ),
        "本年": (
            today.replace(month=1, day=1).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ),
        "近30天": (
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ),
        "近90天": (
            (today - timedelta(days=90)).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ),
        "全部时间": (
            "2000-01-01",
            today.strftime("%Y-%m-%d")
        )
    }


def validate_record(record: Record) -> Tuple[bool, Optional[str]]:
    """
    验证消费记录
    
    Args:
        record: 消费记录对象
        
    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误信息)
    """
    if not record:
        return False, "记录不能为空"
    
    if record.amount <= 0:
        return False, "消费金额必须大于0"
    
    if record.amount > 1000000:
        return False, "消费金额不能超过100万"
    
    if not record.date:
        return False, "日期不能为空"
    
    try:
        datetime.strptime(record.date, "%Y-%m-%d")
    except ValueError:
        return False, "日期格式不正确，请使用 YYYY-MM-DD 格式"
    
    if not record.description or len(record.description.strip()) == 0:
        return False, "消费描述不能为空"
    
    if len(record.description) > 100:
        return False, "消费描述不能超过100个字符"
    
    if record.note and len(record.note) > 500:
        return False, "备注不能超过500个字符"
    
    return True, None


def calculate_statistics(records: List[Record]) -> Dict:
    """
    计算消费统计信息
    
    Args:
        records: 消费记录列表
        
    Returns:
        Dict: 统计数据字典
    """
    if not records:
        return {
            "total": 0,
            "count": 0,
            "avg": 0,
            "max": 0,
            "min": 0,
            "max_date": "-",
            "min_date": "-",
            "categories": {},
            "daily_avg": 0
        }
    
    amounts = [r.amount for r in records]
    total = sum(amounts)
    count = len(amounts)
    
    # 按金额排序找最大最小
    sorted_records = sorted(records, key=lambda x: x.amount, reverse=True)
    
    return {
        "total": total,
        "count": count,
        "avg": total / count if count > 0 else 0,
        "max": max(amounts) if amounts else 0,
        "min": min(amounts) if amounts else 0,
        "max_date": sorted_records[0].date if sorted_records else "-",
        "min_date": sorted_records[-1].date if sorted_records else "-",
        "categories": get_category_statistics(records),
        "daily_avg": calculate_daily_average(records)
    }


def get_category_statistics(records: List[Record]) -> Dict[str, Dict]:
    """
    获取分类统计信息
    
    Args:
        records: 消费记录列表
        
    Returns:
        Dict: 分类统计数据
    """
    category_stats = {}
    
    for record in records:
        cat_name = record.category.value
        
        if cat_name not in category_stats:
            category_stats[cat_name] = {
                "total": 0,
                "count": 0,
                "avg": 0,
                "max": 0,
                "min": float('inf') if records else 0
            }
        
        stats = category_stats[cat_name]
        stats["total"] += record.amount
        stats["count"] += 1
        stats["max"] = max(stats["max"], record.amount)
        if stats["min"] != float('inf'):
            stats["min"] = min(stats["min"], record.amount)
    
    # 计算平均值
    for stats in category_stats.values():
        if stats["count"] > 0:
            stats["avg"] = stats["total"] / stats["count"]
        if stats["min"] == float('inf'):
            stats["min"] = 0
    
    return category_stats


def calculate_daily_average(records: List[Record]) -> float:
    """
    计算日均消费
    
    Args:
        records: 消费记录列表
        
    Returns:
        float: 日均消费金额
    """
    if not records:
        return 0
    
    # 获取日期范围
    dates = [datetime.strptime(r.date, "%Y-%m-%d") for r in records]
    min_date = min(dates)
    max_date = max(dates)
    
    # 计算天数（至少1天）
    days = (max_date - min_date).days + 1
    
    total = sum(r.amount for r in records)
    return total / max(days, 1)


def export_to_csv(records: List[Record], filename: str = None) -> str:
    """
    导出记录为CSV文件
    
    Args:
        records: 消费记录列表
        filename: 文件名（可选）
        
    Returns:
        str: 导出文件的绝对路径
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"消费记录_{timestamp}.csv"
    
    # 确保导出目录存在
    export_dir = Path("exports")
    export_dir.mkdir(exist_ok=True)
    
    filepath = export_dir / filename
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow(['日期', '分类', '金额', '描述', '备注', '支付方式', '创建时间'])

            # 写入数据
            for record in records:
                writer.writerow([
                    record.date,
                    record.category.value,
                    record.amount,
                    record.description,
                    record.note or '',
                    getattr(record, 'payment', '现金'),
                    record.created_at
                ])
        
        return str(filepath.absolute())
    except Exception as e:
        raise IOError(f"导出CSV失败: {e}")


def import_from_csv(filepath: str) -> List[Record]:
    """
    从CSV文件导入记录

    Args:
        filepath: CSV文件路径

    Returns:
        List[Record]: 导入的消费记录列表
    """
    records = []

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cat_name = row.get('分类', '').strip()
                    record = Record(
                        category=Record._parse_category(cat_name) if cat_name else Category.OTHER,
                        amount=float(row.get('金额', 0)),
                        date=row.get('日期', ''),
                        description=row.get('描述', ''),
                        note=row.get('备注') or None,
                        payment=row.get('支付方式', '现金').strip() or '现金',
                    )
                    records.append(record)
                except (ValueError, KeyError) as e:
                    print(f"跳过无效行: {row}, 错误: {e}")
                    continue

        return records
    except Exception as e:
        raise IOError(f"导入CSV失败: {e}")


def get_category_color(category: str) -> str:
    """
    获取分类对应的颜色
    
    Args:
        category: 分类名称
        
    Returns:
        str: 颜色代码
    """
    colors = {
        "餐饮": "#FF6B6B",
        "交通": "#4ECDC4",
        "购物": "#45B7D1",
        "娱乐": "#96CEB4",
        "医疗": "#FFEAA7",
        "通讯": "#DDA0DD",
        "教育": "#98D8C8",
        "居住": "#F7DC6F",
        "其他": "#BDC3C7"
    }
    
    return colors.get(category, "#BDC3C7")


def format_date(date_str: str, format_out: str = "%Y年%m月%d日") -> str:
    """
    格式化日期字符串
    
    Args:
        date_str: 输入日期字符串
        format_out: 输出格式
        
    Returns:
        str: 格式化后的日期字符串
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return date.strftime(format_out)
    except ValueError:
        return date_str


def get_month_name(month: int) -> str:
    """
    获取月份名称
    
    Args:
        month: 月份数字
        
    Returns:
        str: 月份名称
    """
    months = {
        1: "一月", 2: "二月", 3: "三月", 4: "四月",
        5: "五月", 6: "六月", 7: "七月", 8: "八月",
        9: "九月", 10: "十月", 11: "十一月", 12: "十二月"
    }
    return months.get(month, str(month))


def detect_anomalies(records: List[Record], threshold: float = 2.0) -> List[Dict]:
    """
    检测异常消费记录
    
    Args:
        records: 消费记录列表
        threshold: 标准差倍数阈值
        
    Returns:
        List[Dict]: 异常记录列表
    """
    if len(records) < 3:
        return []
    
    amounts = [r.amount for r in records]
    mean = sum(amounts) / len(amounts)
    variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
    std = variance ** 0.5
    
    anomalies = []
    
    for record in records:
        z_score = (record.amount - mean) / std if std > 0 else 0
        
        if abs(z_score) > threshold:
            anomalies.append({
                "record": record,
                "z_score": z_score,
                "deviation": record.amount - mean
            })
    
    return anomalies


def calculate_budget_status(records: List[Record], budget: float) -> Dict:
    """
    计算预算状态
    
    Args:
        records: 消费记录列表
        budget: 预算金额
        
    Returns:
        Dict: 预算状态信息
    """
    total = sum(r.amount for r in records)
    remaining = budget - total
    percentage = (total / budget * 100) if budget > 0 else 0
    
    status = "normal"
    if percentage >= 100:
        status = "over"
    elif percentage >= 80:
        status = "warning"
    
    return {
        "budget": budget,
        "spent": total,
        "remaining": remaining,
        "percentage": percentage,
        "status": status,
        "is_over": total > budget
    }


def calculate_weekday_analysis(records: List[Record]) -> Dict:
    """
    计算周规律分析
    
    Args:
        records: 消费记录列表
        
    Returns:
        Dict: 周规律统计数据
    """
    from datetime import datetime
    
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_totals = {i: 0.0 for i in range(7)}
    weekday_counts = {i: 0 for i in range(7)}
    
    for record in records:
        try:
            d = datetime.strptime(record.date, "%Y-%m-%d")
            wd = d.weekday()  # 0=Monday, 6=Sunday
            weekday_totals[wd] += record.amount
            weekday_counts[wd] += 1
        except:
            continue
    
    weekday_stats = {}
    for i in range(7):
        avg = weekday_totals[i] / weekday_counts[i] if weekday_counts[i] > 0 else 0
        weekday_stats[weekday_names[i]] = {
            "total": round(weekday_totals[i], 2),
            "count": weekday_counts[i],
            "average": round(avg, 2)
        }
    
    return weekday_stats


def calculate_trend_forecast(records: List[Record], days: int = 7) -> Dict:
    """
    计算趋势预测（简单移动平均）
    
    Args:
        records: 消费记录列表
        days: 移动平均窗口天数
        
    Returns:
        Dict: 趋势预测数据
    """
    from datetime import datetime, timedelta
    
    if not records:
        return {"forecast": [], "trend": "平稳", "moving_averages": []}
    
    # 按日期聚合
    daily_totals = {}
    for r in records:
        daily_totals[r.date] = daily_totals.get(r.date, 0) + r.amount
    
    sorted_dates = sorted(daily_totals.keys())
    if len(sorted_dates) < days:
        return {
            "forecast": [],
            "trend": "数据不足",
            "moving_averages": [],
            "message": f"需要至少{days}天的数据"
        }
    
    # 移动平均
    moving_averages = []
    for i in range(len(sorted_dates) - days + 1):
        window_data = [daily_totals[sorted_dates[i + j]] for j in range(days)]
        avg = sum(window_data) / days
        moving_averages.append({
            "date": sorted_dates[i + days - 1],
            "average": round(avg, 2)
        })
    
    # 简单线性回归
    if len(moving_averages) >= 3:
        n = len(moving_averages)
        x_vals = list(range(n))
        y_vals = [ma["average"] for ma in moving_averages]
        
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n
        
        numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
        
        if denominator != 0:
            slope = numerator / denominator
            trend = "上升" if slope > 5 else "下降" if slope < -5 else "平稳"
        else:
            slope = 0
            trend = "平稳"
    else:
        slope = 0
        trend = "数据不足"
    
    return {
        "forecast": [],
        "trend": trend,
        "trend_slope": round(slope, 4),
        "moving_averages": moving_averages
    }
