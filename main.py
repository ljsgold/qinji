"""
杭州电子科技大学《Python程序设计》期末大作业
个人消费管理系统 - Starlette 后端（增强版）

学号：249050123
姓名：刘俊昇

增强功能：
- 异常消费检测（Z-score算法）
- 周规律分析
- 趋势预测（移动平均）
- 预算预警系统
"""

from starlette.applications import Starlette
from starlette.routing import Route, Mount, Router
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.datastructures import UploadFile
from datetime import datetime, timedelta
import uvicorn
import json
import os
from pathlib import Path
from typing import Optional, List
import math

# 复用业务逻辑
from data_storage import DataStorage
from models import Record, Category
from utils import (
    calculate_statistics,
    validate_record,
    get_date_range_options,
    export_to_csv,
    import_from_csv,
    detect_anomalies,
    calculate_weekday_analysis,
    calculate_trend_forecast,
)


# ── 全局存储 ───────────────────────────────────────────────


# ── JSON 辅助 ─────────────────────────────────────────────

BASE_DIR = Path(__file__).parent


def json_response(data, status=200):
    return JSONResponse(data, status_code=status)


def error_response(msg, status=400):
    return JSONResponse({"detail": msg}, status_code=status)


# ── 路由函数 ──────────────────────────────────────────────

async def root(request: Request):
    frontend_dir = Path(__file__).parent / "frontend"
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return RedirectResponse(url="/frontend/index.html")
    return JSONResponse({"message": "个人消费管理系统 API", "version": "1.0.0"})


# ── 消费记录 CRUD ────────────────────────────────────────

async def get_records(request: Request):
    storage = get_storage()
    records = storage.get_all_records()

    # 查询参数
    category = request.query_params.get("category")
    keyword = request.query_params.get("keyword")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    min_amount = request.query_params.get("min_amount")
    max_amount = request.query_params.get("max_amount")
    payment = request.query_params.get("payment")
    sort = request.query_params.get("sort", "date_desc")
    limit = int(request.query_params.get("limit", 100))
    offset = int(request.query_params.get("offset", 0))

    if category and category != "全部":
        records = [r for r in records if r.category.value == category]
    if keyword:
        kw = keyword.lower()
        records = [r for r in records
                   if kw in r.description.lower()
                   or kw in (r.note or "").lower()
                   or kw in r.category.value.lower()
                   or kw in getattr(r, "payment", "").lower()]
    if start_date:
        records = [r for r in records if r.date >= start_date]
    if end_date:
        records = [r for r in records if r.date <= end_date]
    if min_amount:
        try:
            records = [r for r in records if r.amount >= float(min_amount)]
        except ValueError:
            pass
    if max_amount:
        try:
            records = [r for r in records if r.amount <= float(max_amount)]
        except ValueError:
            pass
    if payment and payment != "全部":
        records = [r for r in records if getattr(r, "payment", None) == payment]

    # 排序
    sort_map = {
        "date_desc": lambda r: r.date,
        "date_asc": lambda r: r.date,
        "amount_desc": lambda r: r.amount,
        "amount_asc": lambda r: r.amount,
    }
    rev = {"date_desc": True, "date_asc": False, "amount_desc": True, "amount_asc": False}
    key = sort_map.get(sort, lambda r: r.date)
    records = sorted(records, key=key, reverse=rev.get(sort, True))

    total = len(records)
    records = records[offset:offset + limit]

    return json_response({"total": total, "records": [r.to_dict() for r in records]})


async def create_record(request: Request):
    storage = get_storage()
    try:
        payload = await request.json()
    except Exception:
        return error_response("无效的 JSON 请求体", 400)

    # 支持多种字段名称（兼容前端）
    category = payload.get("category") or payload.get("分类")
    amount = payload.get("amount") or payload.get("金额")
    date = payload.get("date") or payload.get("日期")
    description = payload.get("description") or payload.get("描述") or payload.get("note", "消费")
    note = payload.get("note") or payload.get("备注")
    payment = payload.get("payment") or payload.get("支付方式", "现金")

    required = ["category", "amount", "date"]
    for field in required:
        if not (payload.get(field) or payload.get({"category": "分类", "amount": "金额", "date": "日期"}.get(field))):
            return error_response(f"缺少必填字段: {field}", 400)

    try:
        record = Record(
            category=Record._parse_category(category),
            amount=float(amount),
            date=date,
            description=description,
            note=note,
            payment=payment,
        )
    except (KeyError, ValueError, Exception) as e:
        return error_response(f"参数错误: {e}", 400)

    is_valid, err_msg = validate_record(record)
    if not is_valid:
        return error_response(err_msg, 400)

    success = storage.add_record(record)
    if not success:
        return error_response("添加记录失败", 500)

    return json_response({"success": True, "record": record.to_dict()})


async def update_record(request: Request):
    record_id = request.path_params.get("record_id")
    storage = get_storage()

    existing = storage.get_record(record_id)
    if not existing:
        return error_response("记录不存在", 404)

    try:
        payload = await request.json()
    except Exception:
        return error_response("无效的 JSON", 400)

    kwargs = {}
    for field in ["category", "amount", "date", "description", "note"]:
        if field in payload:
            kwargs[field] = payload[field]

    success = storage.update_record(record_id, **kwargs)
    if not success:
        return error_response("更新失败", 500)

    return json_response({"success": True})


async def delete_record(request: Request):
    record_id = request.path_params.get("record_id")
    storage = get_storage()
    success = storage.delete_record(record_id)
    if not success:
        return error_response("记录不存在", 404)
    return json_response({"success": True})


# ── 统计 ──────────────────────────────────────────────────

async def get_statistics(request: Request):
    storage = get_storage()
    records = storage.get_all_records()

    category = request.query_params.get("category")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if category and category != "全部":
        records = [r for r in records if r.category.value == category]
    if start_date:
        records = [r for r in records if r.date >= start_date]
    if end_date:
        records = [r for r in records if r.date <= end_date]

    stats = calculate_statistics(records)

    today = datetime.now()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    today_str = today.strftime("%Y-%m-%d")

    all_recs = storage.get_all_records()
    month_total = sum(r.amount for r in all_recs if r.date >= month_start.strftime("%Y-%m-%d"))
    week_total = sum(r.amount for r in all_recs if r.date >= week_start.strftime("%Y-%m-%d"))
    today_total = sum(r.amount for r in all_recs if r.date == today_str)

    return json_response({
        "total": stats.get("total", stats.get("avg", 0) * stats.get("count", 0)),
        "count": stats.get("count", len(records)),
        "average": stats.get("avg", 0),
        "avg": stats.get("avg", 0),
        "max_amount": stats.get("max", 0),
        "max": stats.get("max", 0),
        "min_amount": stats.get("min", 0),
        "min": stats.get("min", 0),
        "month_total": month_total,
        "week_total": week_total,
        "today_total": today_total,
        "daily_avg": stats.get("daily_avg", 0),
    })


# ── 分类 & 日期范围 ──────────────────────────────────────

async def get_categories(request: Request):
    return json_response({"categories": [{"value": c.value, "name": c.name} for c in Category]})


async def get_date_ranges(request: Request):
    ranges = get_date_range_options()
    return json_response({
        "ranges": {k: {"start": v[0], "end": v[1]} for k, v in ranges.items()}
    })


# ── 导出 ──────────────────────────────────────────────────

async def export_csv(request: Request):
    storage = get_storage()
    records = storage.get_all_records()
    if not records:
        return error_response("暂无数据可导出", 400)
    try:
        path = export_to_csv(records)
        return FileResponse(
            path,
            media_type="text/csv; charset=utf-8",
            filename=Path(path).name,
        )
    except Exception as e:
        return error_response(str(e), 500)


async def import_csv(request: Request):
    storage = get_storage()
    try:
        form = await request.form()
        file = form.get("file")
        if not file:
            return error_response("未上传文件", 400)

        import tempfile, shutil
        suffix = Path(file.filename).suffix.lower()
        if suffix not in (".csv", ".txt"):
            return error_response("仅支持 CSV 或 TXT 文件", 400)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            records = import_from_csv(tmp_path)
            added, skipped = 0, 0
            for r in records:
                ok = storage.add_record(r)
                if ok:
                    added += 1
                else:
                    skipped += 1
            return json_response({
                "success": True,
                "added": added,
                "skipped": skipped,
                "message": f"成功导入 {added} 条，跳过 {skipped} 条"
            })
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        return error_response(f"导入失败：{e}", 500)


# ── 数据管理 ─────────────────────────────────────────────

async def clear_records(request: Request):
    storage = get_storage()
    success = storage.clear_all()
    return json_response({"success": success})


async def create_backup(request: Request):
    storage = get_storage()
    path = storage.create_backup()
    return json_response({"success": True, "path": path})


async def list_backups(request: Request):
    storage = get_storage()
    backups = list(storage.backup_dir.glob("*.json"))
    backups = sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)
    return json_response({
        "backups": [{"name": b.name, "path": str(b).replace("\\", "/")} for b in backups]
    })


async def restore_backup(request: Request):
    path = request.query_params.get("path")
    if not path:
        return error_response("缺少 path 参数", 400)
    # 将正斜杠转换为反斜杠（兼容Windows）
    path = path.replace("/", "\\")
    storage = get_storage()
    success = storage.restore_backup(path)
    return json_response({"success": success})


async def read_backup(request: Request):
    import urllib.parse
    path = urllib.parse.unquote(request.query_params.get("path", ""))
    if not path:
        return error_response("缺少 path 参数", 400)
    # 将正斜杠转换为反斜杠（兼容Windows）
    path = path.replace("/", "\\")
    storage = get_storage()
    try:
        records = storage.read_backup_file(path)
        return json_response({"records": [r.to_dict() for r in records]})
    except Exception as e:
        return error_response(f"读取失败: {e}", 500)


async def delete_backup(request: Request):
    import urllib.parse
    path = urllib.parse.unquote(request.query_params.get("path", ""))
    if not path:
        return error_response("缺少 path 参数", 400)
    # 将正斜杠转换为反斜杠（兼容Windows）
    path = path.replace("/", "\\")
    storage = get_storage()
    try:
        success = storage.delete_backup_file(path)
        return json_response({"success": success})
    except Exception as e:
        return error_response(f"删除失败: {e}", 500)


import sys
async def get_py_version(request: Request):
    return json_response({"version": sys.version.split()[0]})


async def get_record_count(request: Request):
    storage = get_storage()
    records = storage.get_all_records()
    return json_response({"count": len(records)})


# ── 异常消费检测 ─────────────────────────────────────────

async def get_anomalies(request: Request):
    """
    异常消费检测API
    使用Z-score算法检测异常消费记录
    """
    storage = get_storage()
    records = storage.get_all_records()

    if len(records) < 3:
        return json_response({"anomalies": [], "message": "数据量不足，无法进行异常检测"})

    amounts = [r.amount for r in records]
    mean = sum(amounts) / len(amounts)
    variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
    std = math.sqrt(variance) if variance > 0 else 0

    anomalies = []
    threshold = 2.0  # Z-score阈值

    for r in records:
        z_score = (r.amount - mean) / std if std > 0 else 0
        if abs(z_score) > threshold:
            anomalies.append({
                "id": r.id,
                "date": r.date,
                "category": r.category.value,
                "description": r.description,
                "amount": r.amount,
                "z_score": round(z_score, 2),
                "deviation": round(r.amount - mean, 2),
                "mean": round(mean, 2),
                "std": round(std, 2)
            })

    # 按z_score绝对值降序排列
    anomalies.sort(key=lambda x: abs(x["z_score"]), reverse=True)

    return json_response({
        "anomalies": anomalies,
        "total": len(anomalies),
        "threshold": threshold,
        "mean": round(mean, 2),
        "std": round(std, 2),
        "message": f"检测到 {len(anomalies)} 条异常消费记录" if anomalies else "未检测到明显异常"
    })


# ── 周规律分析 ───────────────────────────────────────────

async def get_weekday_analysis(request: Request):
    """
    周规律分析API
    分析每周各天的消费规律
    """
    storage = get_storage()
    records = storage.get_all_records()

    if not records:
        return json_response({
            "weekday_stats": {},
            "highest_day": None,
            "lowest_day": None,
            "anomalies": []
        })

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_totals = {i: 0.0 for i in range(7)}
    weekday_counts = {i: 0 for i in range(7)}
    weekday_records = {i: [] for i in range(7)}

    for r in records:
        try:
            d = datetime.strptime(r.date, "%Y-%m-%d")
            wd = d.weekday()  # 0=Monday, 6=Sunday
            weekday_totals[wd] += r.amount
            weekday_counts[wd] += 1
            weekday_records[wd].append(r.to_dict())
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

    # 找出消费最高和最低的日期
    avgs = {weekday_names[i]: weekday_totals[i] / weekday_counts[i] if weekday_counts[i] > 0 else 0 for i in range(7)}
    non_zero_avgs = {k: v for k, v in avgs.items() if v > 0}

    highest_day = max(non_zero_avgs, key=non_zero_avgs.get) if non_zero_avgs else None
    lowest_day = min(non_zero_avgs, key=non_zero_avgs.get) if non_zero_avgs else None

    # 检测日异常（当天消费远超平均）
    anomalies = []
    overall_avg = sum(weekday_totals.values()) / max(sum(weekday_counts.values()), 1)
    for wd, records_list in weekday_records.items():
        for r in records_list:
            if r["amount"] > overall_avg * 2.5:
                anomalies.append({
                    "date": r["date"],
                    "amount": r["amount"],
                    "category": r["category"],
                    "description": r["description"],
                    "deviation": round(r["amount"] - overall_avg, 2)
                })

    return json_response({
        "weekday_stats": weekday_stats,
        "highest_day": {
            "name": highest_day,
            "average": round(avgs.get(highest_day, 0), 2) if highest_day else None
        },
        "lowest_day": {
            "name": lowest_day,
            "average": round(avgs.get(lowest_day, 0), 2) if lowest_day else None
        },
        "anomalies": anomalies[:5],  # 最多返回5条
        "total_records": len(records)
    })


# ── 趋势预测 ─────────────────────────────────────────────

async def get_trend_forecast(request: Request):
    """
    趋势预测API
    使用简单移动平均预测未来消费趋势
    """
    storage = get_storage()
    records = storage.get_all_records()

    if len(records) < 7:
        return json_response({
            "message": "数据量不足，无法进行趋势预测",
            "forecast": None
        })

    # 按日期聚合每日消费
    daily_totals = {}
    for r in records:
        daily_totals[r.date] = daily_totals.get(r.date, 0) + r.amount

    # 排序
    sorted_dates = sorted(daily_totals.keys())

    # 计算7天移动平均
    window = min(7, len(sorted_dates))
    moving_averages = []
    for i in range(len(sorted_dates) - window + 1):
        window_data = [daily_totals[sorted_dates[i + j]] for j in range(window)]
        avg = sum(window_data) / window
        moving_averages.append({
            "date": sorted_dates[i + window - 1],
            "average": round(avg, 2)
        })

    # 简单线性回归预测未来3天
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
            intercept = y_mean - slope * x_mean

            # 预测未来3天
            forecast = []
            last_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")
            for i in range(1, 4):
                future_date = last_date + timedelta(days=i)
                predicted = slope * (n + i - 1) + intercept
                forecast.append({
                    "date": future_date.strftime("%Y-%m-%d"),
                    "predicted_amount": round(max(0, predicted), 2),
                    "confidence": "low" if n < 14 else "medium" if n < 30 else "high"
                })

            trend = "上升" if slope > 5 else "下降" if slope < -5 else "平稳"
            trend_slope = round(slope, 4)
        else:
            forecast = []
            trend = "平稳"
            trend_slope = 0
    else:
        forecast = []
        trend = "数据不足"
        trend_slope = 0

    return json_response({
        "moving_averages": moving_averages,
        "forecast": forecast,
        "trend": trend,
        "trend_slope": trend_slope,
        "data_points": len(sorted_dates),
        "message": f"消费趋势{trend}，日均变化约 {abs(trend_slope):.2f} 元" if trend != "数据不足" else "数据量不足"
    })


# ── 首页摘要 ─────────────────────────────────────────────

async def get_summary(request: Request):
    storage = get_storage()
    records = storage.get_all_records()

    today = datetime.now()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    today_str = today.strftime("%Y-%m-%d")

    month_total = sum(r.amount for r in records if r.date >= month_start.strftime("%Y-%m-%d"))
    week_total = sum(r.amount for r in records if r.date >= week_start.strftime("%Y-%m-%d"))
    today_total = sum(r.amount for r in records if r.date == today_str)

    cat_totals = {}
    for r in records:
        cat_totals[r.category.value] = cat_totals.get(r.category.value, 0) + r.amount

    recent = sorted(records, key=lambda x: x.date, reverse=True)[:5]

    dates = set(r.date for r in records)
    avg_daily = month_total / max(len(dates), 1) if records else 0.0

    return json_response({
        "total_count": len(records),
        "month_total": month_total,
        "week_total": week_total,
        "today_total": today_total,
        "avg_daily": avg_daily,
        "category_totals": cat_totals,
        "recent_records": [r.to_dict() for r in recent],
    })


async def health(request: Request):
    return json_response({"status": "ok", "service": "个人消费管理系统 API", "version": "1.0.0"})


# ── 启动初始化 ────────────────────────────────────────────

_storage: DataStorage = None


def get_storage() -> DataStorage:
    global _storage
    if _storage is None:
        _storage = DataStorage()
        _storage.load_data()
        sample_records = [
            Record(Record._parse_category("餐饮"), 45.5, "2026-05-01", "食堂午餐", "早餐：8元"),
            Record(Record._parse_category("餐饮"), 120.0, "2026-05-01", "餐厅晚餐", "和朋友聚餐"),
            Record(Record._parse_category("交通"), 15.0, "2026-05-02", "地铁出行", "上班通勤"),
            Record(Record._parse_category("购物"), 299.0, "2026-05-03", "购买书籍", "Python编程书籍"),
            Record(Record._parse_category("娱乐"), 80.0, "2026-05-04", "看电影", "周末放松"),
            Record(Record._parse_category("餐饮"), 35.0, "2026-05-05", "外卖", "加班晚餐"),
            Record(Record._parse_category("购物"), 159.0, "2026-05-06", "日用品", "超市购物"),
            Record(Record._parse_category("交通"), 25.0, "2026-05-07", "打车", "紧急外出"),
            Record(Record._parse_category("餐饮"), 68.0, "2026-05-08", "奶茶零食", "下午茶"),
            Record(Record._parse_category("医疗"), 150.0, "2026-05-10", "买药", "感冒药"),
            Record(Record._parse_category("餐饮"), 88.0, "2026-05-12", "生日聚餐", "室友生日"),
            Record(Record._parse_category("购物"), 399.0, "2026-05-15", "衣服", "夏装"),
            Record(Record._parse_category("娱乐"), 200.0, "2026-05-18", "演唱会", "音乐节"),
            Record(Record._parse_category("餐饮"), 42.0, "2026-05-20", "食堂午餐", "工作日"),
            Record(Record._parse_category("交通"), 50.0, "2026-05-22", "火车票", "回家"),
            Record(Record._parse_category("购物"), 89.0, "2026-05-25", "护肤品", "日常护理"),
            Record(Record._parse_category("餐饮"), 56.0, "2026-05-27", "外卖", "周末宅家"),
            Record(Record._parse_category("通讯"), 50.0, "2026-05-28", "手机话费", "月租"),
        ]
        if not _storage.get_all_records():
            for r in sample_records:
                _storage.add_record(r)
        print("[OK] Data loaded, sample records ready.")
    return _storage


# ── 路由表 ───────────────────────────────────────────────

routes = [
    Route("/", root),
    Route("/api/health", health, methods=["GET"]),
    Route("/api/records", get_records, methods=["GET"]),
    Route("/api/records", create_record, methods=["POST"]),
    Route("/api/records/{record_id}", update_record, methods=["PUT"]),
    Route("/api/records/{record_id}", delete_record, methods=["DELETE"]),
    Route("/api/records/clear", clear_records, methods=["POST"]),
    Route("/api/statistics", get_statistics, methods=["GET"]),
    Route("/api/categories", get_categories, methods=["GET"]),
    Route("/api/date-ranges", get_date_ranges, methods=["GET"]),
    Route("/api/export", export_csv, methods=["GET"]),
    Route("/api/import", import_csv, methods=["POST"]),
    Route("/api/backup", create_backup, methods=["POST"]),
    Route("/api/backup/list", list_backups, methods=["GET"]),
    Route("/api/backup/restore", restore_backup, methods=["POST"]),
    Route("/api/backup/read", read_backup, methods=["GET"]),
    Route("/api/backup/delete", delete_backup, methods=["DELETE"]),
    Route("/api/summary", get_summary, methods=["GET"]),
    Route("/api/py-version", get_py_version, methods=["GET"]),
    Route("/api/record-count", get_record_count, methods=["GET"]),
    # 增强功能API
    Route("/api/anomalies", get_anomalies, methods=["GET"]),      # 异常消费检测
    Route("/api/weekday-analysis", get_weekday_analysis, methods=["GET"]),  # 周规律分析
    Route("/api/trend-forecast", get_trend_forecast, methods=["GET"]),      # 趋势预测
]

# 前端静态文件（如果存在）
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.is_dir():
    routes.append(Mount("/frontend", app=StaticFiles(directory=str(frontend_dir), html=True), name="frontend"))


# ── 应用 & CORS ─────────────────────────────────────────

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(routes=routes, middleware=middleware)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
