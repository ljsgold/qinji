"""
API 路由定义

本文件为 FastAPI 版残留，已不再使用。
当前 Web API 基于 Starlette 实现，路由定义在 main.py 中。
保留此文件仅作历史参考。
"""

# 已废弃 — 当前项目使用 Starlette，路由在 main.py 中定义


from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from models import Record, Category
from data_storage import DataStorage
from utils import (
    calculate_statistics,
    validate_record,
    get_date_range_options,
    export_to_csv,
)
from main import get_storage


router = APIRouter(prefix="/api", tags=["消费管理"])


# ──────────────────────────────────────────────
#  消费记录 CRUD
# ──────────────────────────────────────────────

@router.get("/records", summary="获取消费记录列表")
async def get_records(
    category: Optional[str] = Query(None, description="按分类筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    sort: str = Query("date_desc", description="排序: date_desc|date_asc|amount_desc|amount_asc"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    storage = get_storage()
    records = storage.get_all_records()

    # 分类筛选
    if category and category != "全部":
        records = [r for r in records if r.category.value == category]

    # 关键词搜索
    if keyword:
        kw = keyword.lower()
        records = [
            r for r in records
            if kw in r.description.lower()
            or kw in (r.note or "").lower()
            or kw in r.category.value.lower()
        ]

    # 日期范围筛选
    if start_date:
        records = [
            r for r in records
            if r.date >= start_date
        ]
    if end_date:
        records = [
            r for r in records
            if r.date <= end_date
        ]

    # 排序
    sort_map = {
        "date_desc": lambda r: r.date,
        "date_asc": lambda r: r.date,
        "amount_desc": lambda r: r.amount,
        "amount_asc": lambda r: r.amount,
    }
    reverse_map = {"date_desc": True, "date_asc": False, "amount_desc": True, "amount_asc": False}
    key = sort_map.get(sort, lambda r: r.date)
    reverse = reverse_map.get(sort, True)
    records = sorted(records, key=key, reverse=reverse)

    total = len(records)
    records = records[offset : offset + limit]

    return {
        "total": total,
        "records": [r.to_dict() for r in records],
    }


@router.post("/records", summary="添加消费记录")
async def create_record(payload: dict):
    storage = get_storage()

    try:
        record = Record(
            category=payload["category"],
            amount=float(payload["amount"]),
            date=payload["date"],
            description=payload["description"],
            note=payload.get("note"),
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {e}")

    is_valid, error_msg = validate_record(record)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    success = storage.add_record(record)
    if not success:
        raise HTTPException(status_code=500, detail="添加记录失败")

    return {"success": True, "record": record.to_dict()}


@router.put("/records/{record_id}", summary="更新消费记录")
async def update_record(record_id: str, payload: dict):
    storage = get_storage()

    existing = storage.get_record(record_id)
    if not existing:
        raise HTTPException(status_code=404, detail="记录不存在")

    kwargs = {}
    for field in ["category", "amount", "date", "description", "note"]:
        if field in payload:
            kwargs[field] = payload[field]

    success = storage.update_record(record_id, **kwargs)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    return {"success": True}


@router.delete("/records/{record_id}", summary="删除消费记录")
async def delete_record(record_id: str):
    storage = get_storage()
    success = storage.delete_record(record_id)

    if not success:
        raise HTTPException(status_code=404, detail="记录不存在")

    return {"success": True}


# ──────────────────────────────────────────────
#  统计
# ──────────────────────────────────────────────

@router.get("/statistics", summary="获取统计数据")
async def get_statistics(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    storage = get_storage()
    records = storage.get_all_records()

    if category and category != "全部":
        records = [r for r in records if r.category.value == category]
    if start_date:
        records = [r for r in records if r.date >= start_date]
    if end_date:
        records = [r for r in records if r.date <= end_date]

    stats = calculate_statistics(records)

    # 补充月份/周/今日汇总
    today = datetime.now()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())

    month_records = [r for r in storage.get_all_records() if r.date >= month_start.strftime("%Y-%m-%d")]
    week_records = [r for r in storage.get_all_records() if r.date >= week_start.strftime("%Y-%m-%d")]
    today_str = today.strftime("%Y-%m-%d")

    return {
        **stats,
        "month_total": sum(r.amount for r in month_records),
        "week_total": sum(r.amount for r in week_records),
        "today_total": sum(r.amount for r in storage.get_all_records() if r.date == today_str),
    }


# ──────────────────────────────────────────────
#  分类 & 枚举
# ──────────────────────────────────────────────

@router.get("/categories", summary="获取所有分类")
async def get_categories():
    return {"categories": [{"value": c.value, "name": c.name} for c in Category]}


@router.get("/date-ranges", summary="获取预设日期范围")
async def get_preset_date_ranges():
    ranges = get_date_range_options()
    return {
        "ranges": {
            k: {"start": v[0], "end": v[1]}
            for k, v in ranges.items()
        }
    }


# ──────────────────────────────────────────────
#  导出
# ──────────────────────────────────────────────

@router.get("/export", summary="导出为 CSV")
async def export_csv():
    storage = get_storage()
    records = storage.get_all_records()

    if not records:
        raise HTTPException(status_code=400, detail="暂无数据可导出")

    try:
        path = export_to_csv(records)
        filename = Path(path).name
        return {"success": True, "file": filename, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
#  数据管理
# ──────────────────────────────────────────────

@router.post("/records/clear", summary="清空所有记录")
async def clear_records():
    storage = get_storage()
    success = storage.clear_all()
    return {"success": success}


@router.post("/backup", summary="创建备份")
async def create_backup():
    storage = get_storage()
    path = storage.create_backup()
    return {"success": True, "path": path}


@router.get("/backup/list", summary="列出备份文件")
async def list_backups():
    storage = get_storage()
    backups = list(storage.backup_dir.glob("*.json"))
    return {
        "backups": [
            {"name": b.name, "path": str(b)}
            for b in sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)
        ]
    }


@router.post("/backup/restore", summary="恢复备份")
async def restore_backup(path: str = Query(...)):
    storage = get_storage()
    success = storage.restore_backup(path)
    return {"success": success}


# ──────────────────────────────────────────────
#  摘要（供首页快速展示）
# ──────────────────────────────────────────────

@router.get("/summary", summary="首页摘要数据")
async def get_summary():
    storage = get_storage()
    records = storage.get_all_records()

    today = datetime.now()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    today_str = today.strftime("%Y-%m-%d")

    month_total = sum(r.amount for r in records if r.date >= month_start.strftime("%Y-%m-%d"))
    week_total = sum(r.amount for r in records if r.date >= week_start.strftime("%Y-%m-%d"))
    today_total = sum(r.amount for r in records if r.date == today_str)

    # 按分类汇总
    cat_totals = {}
    for r in records:
        cat_totals[r.category.value] = cat_totals.get(r.category.value, 0) + r.amount

    # 最近 5 条
    recent = sorted(records, key=lambda x: x.date, reverse=True)[:5]

    # 日均
    if records:
        dates = set(r.date for r in records)
        avg_daily = month_total / max(len(dates), 1)
    else:
        avg_daily = 0.0

    return {
        "total_count": len(records),
        "month_total": month_total,
        "week_total": week_total,
        "today_total": today_total,
        "avg_daily": avg_daily,
        "category_totals": cat_totals,
        "recent_records": [r.to_dict() for r in recent],
    }
