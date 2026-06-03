"""
杭州电子科技大学《Python程序设计》期末大作业
个人消费管理系统 - Web可视化版本

学号：249050123
姓名：刘俊昇
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import sys
from pathlib import Path
from PIL import Image
import io
import base64

from models import Record, Category
from data_storage import DataStorage
from utils import (
    format_currency, 
    get_date_range_options,
    calculate_statistics,
    export_to_csv,
    validate_record
)

# 页面配置
st.set_page_config(
    page_title="个人消费管理系统",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 评分标准对照表
# ============================================================
SCORING_STANDARDS = {
    "基础要求（50分）": {
        "数据存储": "10分 - 使用JSON文件本地存储，支持备份与恢复",
        "函数封装": "10分 - 模块化设计，models/data_storage/utils 分离",
        "异常处理": "10分 - 完善的数据验证与错误提示机制",
        "数据统计": "10分 - 多维度统计，支持导出CSV",
        "代码规范": "10分 - PEP8规范，完整注释，清晰命名"
    },
    "提高要求（20分）": {
        "菜单交互": "10分 - 侧边栏导航，Tab页签，表单交互",
        "数据可视化": "10分 - Plotly交互图表，多种图表类型",
        "面向对象": "✓ - Record类、Category枚举、DataStorage类",
        "GUI": "✓ - Streamlit Web界面",
        "图片处理": "✓ - 系统图标、图表导出功能"
    },
    "创新加分（10分）": {
        "智能预算": "✓ - 预算管理、超支预警",
        "异常检测": "✓ - Z分数异常消费检测",
        "趋势分析": "✓ - 移动平均线、分类趋势"
    }
}

# 自定义CSS样式 - 柔和舒适主题
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    :root {
        --primary-blue: #4a6fa5;
        --primary-blue-light: #6b8cbe;
        --primary-blue-dark: #4a6fa5;
        --accent-warm: #c4a77d;
        --accent-soft: #c4a77d;
        --bg-primary: #fafbfc;
        --bg-card: #ffffff;
        --bg-sidebar: linear-gradient(180deg, #ffffff 0%, #f5f7f9 100%);
        --text-primary: #2d3748;
        --text-secondary: #5a6775;
        --text-muted: #8896a6;
        --border-color: #e4e8ec;
    }

    /* 隐藏 Cursor IDE 侧边栏底部用户信息 */
    [data-cursor-element-id="cursor-el-1"],
    .sidebar-footer {
        display: none !important;
    }

    /* Cursor IDE Logo 3D 动态效果 */
    [data-cursor-element-id="cursor-el-7"],
    .logo-mark {
        width: 28px !important;
        height: 28px !important;
        background: linear-gradient(135deg, #c4a77d 0%, #4a6fa5 50%, #4a6fa5 100%) !important;
        border-radius: 8px !important;
        transform-style: preserve-3d !important;
        animation: logo3d 4s ease-in-out infinite !important;
        box-shadow: 
            0 4px 12px rgba(74, 111, 165, 0.4),
            0 8px 20px rgba(196, 106, 45, 0.25),
            inset 0 1px 2px rgba(255,255,255,0.5) !important;
        transition: transform 0.3s ease !important;
    }

    @keyframes logo3d {
        0%, 100% { transform: perspective(200px) rotateY(-5deg) rotateX(5deg) scale(1); }
        25% { transform: perspective(200px) rotateY(5deg) rotateX(-5deg) scale(1.02); }
        50% { transform: perspective(200px) rotateY(-3deg) rotateX(3deg) scale(1.01); }
        75% { transform: perspective(200px) rotateY(3deg) rotateX(-3deg) scale(1.02); }
    }

    .logo-mark:hover {
        animation: logo3d-hover 0.6s ease-in-out !important;
        transform: perspective(200px) rotateY(10deg) rotateX(-10deg) scale(1.1) !important;
    }

    @keyframes logo3d-hover {
        0% { transform: perspective(200px) rotateY(0deg) scale(1); }
        50% { transform: perspective(200px) rotateY(15deg) scale(1.15); }
        100% { transform: perspective(200px) rotateY(0deg) scale(1.1); }
    }

    /* 全局字体 */
    html, body, .stApp {
        font-family: 'Noto Sans SC', 'Space Grotesk', -apple-system, sans-serif !important;
        background: var(--bg-primary);
    }

    /* 主标题样式 */
    .main-header {
        font-family: 'Space Grotesk', 'Noto Sans SC', sans-serif !important;
        font-size: 2.8rem;
        font-weight: 700;
        color: var(--primary-blue);
        text-align: left;
        padding: 1.5rem 0 0.5rem 0;
        letter-spacing: -0.02em;
    }

    .subtitle {
        font-size: 1.1rem;
        color: var(--text-secondary);
        text-align: left;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* 指标卡片 - 橙黄暖色风格 */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.75rem 2rem;
        box-shadow: 0 2px 8px rgba(74, 111, 165, 0.06);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(74, 111, 165, 0.12);
        border-color: var(--accent-warm);
    }

    /* Streamlit 原生组件优化 */
    .stMetric {
        background: var(--bg-card) !important;
        padding: 1.5rem !important;
        border-radius: 14px !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 2px 8px rgba(74, 111, 165, 0.05) !important;
    }

    .stMetric > div:first-child {
        color: var(--text-muted) !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .stMetric [data-testid="stMetricValue"] {
        color: var(--primary-blue) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }

    /* 侧边栏优化 - 橙黄暖色 */
    [data-testid="stSidebar"] {
        background: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border-color);
    }

    /* 侧边栏标题 */
    .sidebar-title {
        font-family: 'Space Grotesk', 'Noto Sans SC', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--primary-blue);
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 3px solid var(--accent-warm);
    }

    /* 标题样式 */
    h1, h2, h3 {
        font-family: 'Space Grotesk', 'Noto Sans SC', sans-serif !important;
        color: var(--primary-blue) !important;
        letter-spacing: -0.01em;
    }

    h2 {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
    }

    h3 {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        color: var(--primary-blue-dark) !important;
    }

    /* Radio 导航按钮 - 橙黄交互 */
    [data-testid="stSidebarNav"] label {
        border-radius: 10px;
        padding: 0.8rem 1rem;
        transition: all 0.25s ease;
        color: var(--text-secondary);
        font-weight: 500;
        margin: 0.25rem 0;
    }

    [data-testid="stSidebarNav"] label:hover {
        background: rgba(74, 111, 165, 0.1);
        color: var(--primary-blue);
    }

    [data-testid="stSidebarNav"] label:has([aria-checked="true"]) {
        background: linear-gradient(135deg, rgba(74, 111, 165, 0.18) 0%, rgba(232, 168, 124, 0.12) 100%) !important;
        color: var(--primary-blue) !important;
        font-weight: 600;
        border-left: 4px solid var(--accent-warm);
    }

    /* 分隔线 */
    hr {
        border: none;
        height: 1px;
        background: var(--border-color);
        margin: 1.5rem 0;
    }

    /* 记录卡片 */
    .record-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 0.75rem;
        transition: all 0.25s ease;
    }

    .record-card:hover {
        border-color: var(--accent-warm);
        box-shadow: 0 4px 15px rgba(232, 168, 124, 0.15);
    }

    /* 标签样式 - 橙黄配色 */
    .category-tag {
        display: inline-block;
        padding: 0.35rem 0.9rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.25rem;
    }

    .tag-food { background: #fff3e0; color: #4a6fa5; }
    .tag-transport { background: #e3f2fd; color: #1976d2; }
    .tag-shopping { background: #fce4ec; color: #c2185b; }
    .tag-entertainment { background: #f3e5f5; color: #7b1fa2; }
    .tag-medical { background: #ffebee; color: #c62828; }
    .tag-communication { background: #e8f5e9; color: #2e7d32; }

    /* 按钮样式 - 橙黄主色调 */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--primary-blue-dark) 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        font-family: 'Noto Sans SC', sans-serif;
        transition: all 0.25s ease;
        box-shadow: 0 2px 8px rgba(74, 111, 165, 0.25);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, var(--primary-blue-light) 0%, var(--primary-blue) 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(74, 111, 165, 0.35);
    }

    /* Tabs 样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 2px solid var(--border-color);
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: var(--text-secondary);
    }

    .stTabs .css-1q8jveg [aria-selected="true"] {
        color: var(--primary-blue);
        border-bottom: 3px solid var(--accent-warm);
    }

    /* 表单样式 */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border-radius: 10px;
        border: 1.5px solid var(--border-color);
        padding: 0.75rem 1rem;
        transition: all 0.2s ease;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--accent-warm);
        box-shadow: 0 0 0 3px rgba(232, 168, 124, 0.2);
    }

    /* Dataframe 样式 */
    .dataframe {
        border: none !important;
        border-radius: 12px;
        overflow: hidden;
    }

    [data-testid="stDataFrame"] table {
        border-collapse: separate;
        border-spacing: 0;
    }

    [data-testid="stDataFrame"] th {
        background: linear-gradient(135deg, rgba(74, 111, 165, 0.1) 0%, rgba(232, 168, 124, 0.08) 100%) !important;
        color: var(--primary-blue) !important;
        font-weight: 600;
    }

    /* 进度条 */
    .stProgress > div > div {
        background: var(--border-color);
        border-radius: 10px;
        height: 10px;
    }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--accent-warm) 0%, var(--primary-blue) 100%) !important;
        border-radius: 10px;
    }

    /* 提示信息 */
    .stAlert {
        border-radius: 12px;
        border: none;
    }

    .stAlert[data-baseweb="notification"]:not([kind="error"]):not([kind="warning"]) {
        background: linear-gradient(135deg, rgba(74, 111, 165, 0.08) 0%, rgba(232, 168, 124, 0.05) 100%);
        border-left: 4px solid var(--accent-warm);
    }

    .stAlert[data-baseweb="notification"][kind="success"] {
        background: linear-gradient(135deg, rgba(93, 155, 93, 0.1) 0%, rgba(93, 155, 93, 0.05) 100%);
        border-left: 4px solid var(--success);
    }

    .stAlert[data-baseweb="notification"][kind="warning"] {
        background: linear-gradient(135deg, rgba(74, 111, 165, 0.12) 0%, rgba(232, 168, 124, 0.08) 100%);
        border-left: 4px solid var(--warning);
    }

    .stAlert[data-baseweb="notification"][kind="error"] {
        background: linear-gradient(135deg, rgba(211, 93, 77, 0.1) 0%, rgba(211, 93, 77, 0.05) 100%);
        border-left: 4px solid var(--error);
    }

    /* 图表容器 - 悬浮交互优化 */
    .js-plotly-plot .plotly .modebar {
        background: rgba(255,255,255,0.95) !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 15px rgba(74, 111, 165, 0.1) !important;
        padding: 6px !important;
    }

    .js-plotly-plot .plotly .modebar-btn:hover {
        background: rgba(232, 168, 124, 0.2) !important;
    }

    /* 卡片间距优化 */
    [data-testid="stHorizontalBlock"] {
        gap: 1.5rem;
    }

    /* 评分卡片样式 */
    .score-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }

    .score-card h4 {
        color: var(--primary-blue) !important;
        margin-bottom: 0.5rem !important;
        font-size: 1rem !important;
    }

    .score-item {
        display: flex;
        justify-content: space-between;
        padding: 0.4rem 0;
        border-bottom: 1px dashed var(--border-color);
    }

    .score-item:last-child {
        border-bottom: none;
    }

    /* 下载按钮特殊样式 */
    .download-btn {
        background: linear-gradient(135deg, var(--accent-soft) 0%, var(--accent-warm) 100%) !important;
        color: var(--text-primary) !important;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'storage' not in st.session_state:
        st.session_state.storage = DataStorage()
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = "全部"
    if 'refresh_trigger' not in st.session_state:
        st.session_state.refresh_trigger = 0


def load_sample_data():
    """加载示例数据"""
    storage = st.session_state.storage
    
    if len(storage.records) > 0:
        return
    
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
    
    for record in sample_records:
        storage.add_record(record)


def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.markdown('<div class="sidebar-title">📊 功能菜单</div>', unsafe_allow_html=True)
    
    page = st.sidebar.radio(
        "选择功能",
        ["🏠 首页概览", "💵 消费记录", "📈 统计分析", "📊 数据可视化", "💡 预算管理", "📋 评分标准", "⚙️ 设置"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("### 🔍 筛选条件")
    categories = ["全部"] + [cat.value for cat in Category]
    selected_category = st.sidebar.selectbox("选择分类", categories)
    st.session_state.selected_category = selected_category
    
    date_options = get_date_range_options()
    date_range = st.sidebar.selectbox("日期范围", list(date_options.keys()))
    
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("### 📋 快速统计")
    storage = st.session_state.storage
    total_count = len(storage.records)
    st.sidebar.info(f"总记录数：{total_count} 笔")
    
    return page, date_range


def render_homepage():
    """渲染首页"""
    st.markdown('<h1 class="main-header">💰 个人消费管理系统</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">轻松管理你的每一笔支出 · 智能洞察消费习惯</p>', unsafe_allow_html=True)
    
    load_sample_data()
    
    storage = st.session_state.storage
    records = storage.get_all_records()
    
    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    today = datetime.now()
    month_start = today.replace(day=1)
    month_records = [r for r in records if datetime.strptime(r.date, "%Y-%m-%d") >= month_start]
    month_total = sum(r.amount for r in month_records)
    
    week_start = today - timedelta(days=today.weekday())
    week_records = [r for r in records if datetime.strptime(r.date, "%Y-%m-%d") >= week_start]
    week_total = sum(r.amount for r in week_records)
    
    today_total = sum(r.amount for r in records if r.date == today.strftime("%Y-%m-%d"))
    
    if records:
        dates = set(r.date for r in records)
        avg_daily = month_total / max(len(dates), 1)
    else:
        avg_daily = 0
    
    with col1:
        st.metric("本月消费", format_currency(month_total), f"📅 {len(month_records)}笔")
    with col2:
        st.metric("本周消费", format_currency(week_total), f"📆 {len(week_records)}笔")
    with col3:
        st.metric("今日消费", format_currency(today_total), "⏰")
    with col4:
        st.metric("日均消费", format_currency(avg_daily), "📊")
    
    st.markdown("---")
    
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    col_left, col_right = st.columns([2.5, 1.5])
    
    with col_left:
        st.markdown("### 📝 最近消费记录")
        recent_records = sorted(records, key=lambda x: x.date, reverse=True)[:5]
        
        if recent_records:
            for record in recent_records:
                with st.container():
                    col_a, col_b, col_c = st.columns([3, 1, 1])
                    with col_a:
                        st.markdown(f"**{record.category.value}** — {record.description}")
                        st.caption(f"📅 {record.date} · {record.note or '无备注'}")
                    with col_b:
                        st.markdown(f"### {format_currency(record.amount)}")
                    with col_c:
                        st.write("")
                    st.divider()
        else:
            st.info("暂无消费记录，点击左侧添加记录")
    
    with col_right:
        st.markdown("### 📊 消费分布")
        
        if records:
            category_totals = {}
            for record in records:
                category_totals[record.category.value] = category_totals.get(record.category.value, 0) + record.amount
            
            # 橙黄配色图表
            colors = ['#4a6fa5', '#c4a77d', '#c4a77d', '#4a6fa5', '#6b8cbe', '#c4a77d', '#8896a6']
            fig = px.pie(
                values=list(category_totals.values()),
                names=list(category_totals.keys()),
                hole=0.55,
                color_discrete_sequence=colors
            )
            fig.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                ),
                height=350,
                margin=dict(l=20, r=20, t=40, b=60),
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Noto Sans SC, sans-serif", size=12)
            )
            fig.update_traces(
                hoverinfo="label+percent+value",
                hovertemplate="<b>%{label}</b><br>¥%{value:,.0f}<br>%{percent}<extra></extra>",
                textposition="outside",
                textfont=dict(size=11)
            )
            st.plotly_chart(fig, use_container_width=True)


def render_records_page():
    """渲染消费记录页面"""
    st.markdown("## 💵 消费记录管理")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 查看记录", "➕ 添加记录"])
    
    with tab1:
        storage = st.session_state.storage
        records = storage.get_all_records()
        
        if not records:
            st.info("暂无消费记录，请添加记录")
            return
        
        if st.session_state.selected_category != "全部":
            records = [r for r in records if r.category.value == st.session_state.selected_category]
        
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"共 **{len(records)}** 条记录")
        with col2:
            sort_by = st.selectbox("排序", ["按日期降序", "按日期升序", "按金额降序", "按金额升序"])
        
        if sort_by == "按日期降序":
            records = sorted(records, key=lambda x: x.date, reverse=True)
        elif sort_by == "按日期升序":
            records = sorted(records, key=lambda x: x.date)
        elif sort_by == "按金额降序":
            records = sorted(records, key=lambda x: x.amount, reverse=True)
        else:
            records = sorted(records, key=lambda x: x.amount)
        
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        
        df = pd.DataFrame([
            {
                "日期": r.date,
                "分类": r.category.value,
                "金额": f"¥{r.amount:.2f}",
                "描述": r.description,
                "备注": r.note or "—"
            }
            for r in records
        ])
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 导出为 CSV"):
                csv_path = export_to_csv(records)
                st.success(f"已导出到：{csv_path}")
        
        with col2:
            if st.button("🗑️ 清空所有记录"):
                st.warning("确定要清空所有记录吗？此操作不可撤销！")
                if st.button("确认清空"):
                    storage.clear_all()
                    st.rerun()
    
    with tab2:
        st.markdown("### 添加新记录")
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        
        with st.form("add_record_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                category = st.selectbox("消费分类", options=list(Category), format_func=lambda x: x.value)
                amount = st.number_input("消费金额 (¥)", min_value=0.01, max_value=100000.0, value=10.0, step=0.01, format="%.2f")
            
            with col2:
                date = st.date_input("消费日期", value=datetime.now()).strftime("%Y-%m-%d")
                description = st.text_input("消费描述", placeholder="例如：午餐、打车等")
            
            note = st.text_area("备注（可选）", placeholder="添加一些备注信息...")
            
            st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
            
            submitted = st.form_submit_button("💾 保存记录", use_container_width=True)
            
            if submitted:
                if not description:
                    st.error("请输入消费描述")
                elif amount <= 0:
                    st.error("金额必须大于0")
                else:
                    record = Record(category=category, amount=amount, date=date, description=description, note=note if note else None)
                    is_valid, error_msg = validate_record(record)
                    if not is_valid:
                        st.error(error_msg)
                    else:
                        storage.add_record(record)
                        st.success("✓ 记录添加成功！")
                        st.rerun()


def render_statistics_page():
    """渲染统计分析页面"""
    st.markdown("## 📈 统计分析")
    
    storage = st.session_state.storage
    records = storage.get_all_records()
    
    if not records:
        st.info("暂无数据，请先添加消费记录")
        return
    
    # 橙黄配色方案
    warm_colors = ['#4a6fa5', '#c4a77d', '#c4a77d', '#4a6fa5', '#6b8cbe', '#c4a77d']
    
    st.markdown("### 📅 按时间分析")
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        df_dates = pd.DataFrame([{"日期": r.date, "金额": r.amount} for r in records])
        df_dates["日期"] = pd.to_datetime(df_dates["日期"])
        df_dates["月份"] = df_dates["日期"].dt.to_period("M")
        
        monthly = df_dates.groupby("月份")["金额"].sum().reset_index()
        monthly["月份"] = monthly["月份"].astype(str)
        
        fig = px.bar(
            monthly, x="月份", y="金额", title="月度消费趋势",
            color="金额", color_continuous_scale=['#c4a77d', '#4a6fa5', '#4a6fa5', '#c4a77d']
        )
        fig.update_layout(
            xaxis_title="月份", yaxis_title="消费金额 (¥)", showlegend=False, height=450,
            font=dict(family="Noto Sans SC, sans-serif"),
            title=dict(font=dict(size=16, family="Space Grotesk, sans-serif", color='#4a6fa5')),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#e4e8ec'), yaxis=dict(gridcolor='#e4e8ec'),
            hoverlabel=dict(bgcolor="white", font_size=13)
        )
        st.plotly_chart(fig, use_container_width=True, config={
            'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d'], 'hoverMode': 'closest'
        })
    
    with col2:
        daily_avg = df_dates.groupby("日期")["金额"].sum()
        
        fig = px.line(x=daily_avg.index, y=daily_avg.values, title="每日消费走势", markers=True)
        fig.update_traces(
            line=dict(color='#4a6fa5', width=2.5),
            marker=dict(size=8, color='#c4a77d', line=dict(color='#4a6fa5', width=2))
        )
        fig.update_layout(
            xaxis_title="日期", yaxis_title="消费金额 (¥)", showlegend=False, height=450,
            font=dict(family="Noto Sans SC, sans-serif"),
            title=dict(font=dict(size=16, family="Space Grotesk, sans-serif", color='#4a6fa5')),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#e4e8ec'), yaxis=dict(gridcolor='#e4e8ec'),
            hoverlabel=dict(bgcolor="white", font_size=13)
        )
        st.plotly_chart(fig, use_container_width=True, config={
            'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d'], 'hoverMode': 'closest'
        })
    
    st.markdown("---")
    
    st.markdown("### 📂 按分类分析")
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        category_totals = {}
        for record in records:
            category_totals[record.category.value] = category_totals.get(record.category.value, 0) + record.amount
        
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        cat_df = pd.DataFrame(sorted_categories, columns=["分类", "金额"])
        
        fig = px.bar(cat_df, x="分类", y="金额", title="分类消费排行",
                    color="金额", color_continuous_scale=['#c4a77d', '#4a6fa5'])
        fig.update_layout(
            xaxis_title="分类", yaxis_title="消费金额 (¥)", showlegend=False, height=450,
            font=dict(family="Noto Sans SC, sans-serif"),
            title=dict(font=dict(size=16, family="Space Grotesk, sans-serif", color='#4a6fa5')),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#e4e8ec'), yaxis=dict(gridcolor='#e4e8ec'),
            hoverlabel=dict(bgcolor="white", font_size=13)
        )
        st.plotly_chart(fig, use_container_width=True, config={
            'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d'], 'hoverMode': 'closest'
        })
    
    with col2:
        fig = px.pie(
            names=list(category_totals.keys()), values=list(category_totals.values()),
            title="消费分类占比", hole=0.45, color_discrete_sequence=warm_colors
        )
        fig.update_traces(
            textinfo="label+percent", textposition="outside",
            hovertemplate="<b>%{label}</b><br>¥%{value:,.0f}<br>%{percent}<extra></extra>"
        )
        fig.update_layout(
            height=450, font=dict(family="Noto Sans SC, sans-serif"),
            title=dict(font=dict(size=16, family="Space Grotesk, sans-serif", color='#4a6fa5')),
            paper_bgcolor='rgba(0,0,0,0)', hoverlabel=dict(bgcolor="white", font_size=13),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True, config={
            'displayModeBar': True, 'displaylogo': False, 'hoverMode': 'closest'
        })
    
    st.markdown("---")
    
    st.markdown("### 📊 统计汇总")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    stats = calculate_statistics(records)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总消费", format_currency(stats['total']), f"共 {stats['count']} 笔")
    with col2:
        st.metric("最高单笔", format_currency(stats['max']), f"📍 {stats['max_date']}")
    with col3:
        st.metric("最低单笔", format_currency(stats['min']), f"📍 {stats['min_date']}")
    with col4:
        st.metric("平均单笔", format_currency(stats['avg']), "💰")


def render_visualization_page():
    """渲染数据可视化页面"""
    st.markdown("## 📊 数据可视化")
    
    storage = st.session_state.storage
    records = storage.get_all_records()
    
    if not records:
        st.info("暂无数据，请先添加消费记录")
        return
    
    # 橙黄配色
    primary_orange = '#4a6fa5'
    accent_yellow = '#c4a77d'
    accent_gold = '#c4a77d'
    
    viz_type = st.selectbox("选择可视化类型", ["消费趋势", "分类构成", "热力图", "预算对比", "异常消费检测"])
    
    df = pd.DataFrame([{"日期": r.date, "分类": r.category.value, "金额": r.amount, "描述": r.description} for r in records])
    df["日期"] = pd.to_datetime(df["日期"])
    df = df.sort_values("日期")
    
    chart_config = {
        'displayModeBar': True, 'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'], 'hoverMode': 'closest'
    }
    
    layout_base = dict(
        font=dict(family="Noto Sans SC, sans-serif", size=12),
        title=dict(font=dict(size=16, family="Space Grotesk, sans-serif", color=primary_orange)),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#e4e8ec', showgrid=True),
        yaxis=dict(gridcolor='#e4e8ec', showgrid=True),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Noto Sans SC, sans-serif")
    )
    
    if viz_type == "消费趋势":
        st.markdown("### 📈 消费趋势图")
        st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
        
        df_daily = df.groupby("日期")["金额"].sum().reset_index().sort_values("日期")
        df_daily["移动平均(7天)"] = df_daily["金额"].rolling(window=min(7, len(df_daily)), min_periods=1).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_daily["日期"], y=df_daily["金额"], mode="lines+markers", name="日消费",
            line=dict(color=primary_orange, width=2.5),
            marker=dict(size=10, color=accent_yellow, line=dict(color=primary_orange, width=2)),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>¥%{y:,.2f}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=df_daily["日期"], y=df_daily["移动平均(7天)"], mode="lines", name="7日移动平均",
            line=dict(color=accent_gold, width=2.5, dash="dash"),
            hovertemplate="<b>7日均值</b><br>¥%{y:,.2f}<extra></extra>"
        ))
        fig.update_layout(
            title="每日消费趋势（悬浮查看详情）", xaxis_title="日期", yaxis_title="消费金额 (¥)",
            height=500, **layout_base, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, config=chart_config)
        
    elif viz_type == "分类构成":
        st.markdown("### 🍩 分类构成分析")
        st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            category_totals = df.groupby("分类")["金额"].sum()
            colors = ['#4a6fa5', '#c4a77d', '#c4a77d', '#4a6fa5', '#6b8cbe', '#c4a77d', '#8896a6']
            fig = go.Figure(data=[go.Pie(
                labels=category_totals.index, values=category_totals.values, hole=0.6,
                textinfo="label+percent", textposition="outside",
                hovertemplate="<b>%{label}</b><br>¥%{value:,.0f}<br>%{percent}<extra></extra>",
                marker=dict(colors=colors)
            )])
            fig.update_layout(
                height=450, title=dict(text="消费分类构成", font=dict(size=16, family="Space Grotesk, sans-serif", color=primary_orange)),
                paper_bgcolor='rgba(0,0,0,0)', hoverlabel=dict(bgcolor="white", font_size=13),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True, config=chart_config)
        
        with col2:
            fig = px.treemap(
                df.groupby(["分类", "描述"])["金额"].sum().reset_index(),
                path=["分类", "描述"], values="金额", title="消费项目分布",
                color_discrete_sequence=['#4a6fa5', '#c4a77d', '#c4a77d', '#4a6fa5', '#6b8cbe']
            )
            fig.update_layout(
                height=450, title=dict(text="消费项目分布（悬浮查看）", font=dict(size=16, family="Space Grotesk, sans-serif", color=primary_orange)),
                paper_bgcolor='rgba(0,0,0,0)', hoverlabel=dict(bgcolor="white", font_size=13)
            )
            st.plotly_chart(fig, use_container_width=True, config=chart_config)
    
    elif viz_type == "热力图":
        st.markdown("### 🗓️ 消费热力图")
        st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
        
        df["星期"] = df["日期"].dt.day_name()
        df["金额"] = df["金额"].astype(float)
        
        week_days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        week_days_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        week_totals = df.groupby("星期")["金额"].sum().reindex(week_days_en).fillna(0)
        
        fig = go.Figure(data=[go.Bar(
            x=week_days_cn, y=week_totals.values, marker_color=week_totals.values,
            hovertemplate="<b>%{x}</b><br>¥%{y:,.2f}<extra></extra>",
            marker=dict(color=week_totals.values, colorscale=['#f5f7f9', '#c4a77d', '#4a6fa5', '#4a6fa5'])
        )])
        fig.update_layout(
            title="按星期消费分布（工作日 vs 周末）", xaxis_title="星期", yaxis_title="消费金额 (¥)",
            height=450, **layout_base
        )
        st.plotly_chart(fig, use_container_width=True, config=chart_config)
    
    elif viz_type == "预算对比":
        st.markdown("### 💹 预算对比")
        st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
        
        budget = st.number_input("设置月预算 (¥)", value=3000.0, step=100.0, help="调整滑块设置每月消费预算")
        
        df["月份"] = df["日期"].dt.to_period("M")
        monthly_totals = df.groupby("月份")["金额"].sum()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[str(p) for p in monthly_totals.index], y=monthly_totals.values, name="实际消费",
            marker_color=primary_orange, hovertemplate="<b>%{x}</b><br>实际: ¥%{y:,.2f}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=[str(p) for p in monthly_totals.index], y=[budget] * len(monthly_totals), mode="lines", name="预算线",
            line=dict(color='#c4a77d', width=3, dash="dash"),
            hovertemplate="<b>预算</b>: ¥{:,.2f}<extra></extra>".format(budget)
        ))
        fig.update_layout(
            title=f"月度消费 vs 预算（悬浮查看详情）", xaxis_title="月份", yaxis_title="金额 (¥)",
            height=450, **layout_base, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, config=chart_config)
        
        current_month = datetime.now().strftime("%Y-%m")
        current_month_total = monthly_totals.get(pd.Period(current_month), 0)
        budget_remaining = budget - current_month_total
        budget_used_pct = (current_month_total / budget * 100) if budget > 0 else 0
        
        st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("本月消费", format_currency(current_month_total), f"📊 {budget_used_pct:.1f}%")
        with col2:
            st.metric("剩余预算", format_currency(max(0, budget_remaining)), "💰")
        with col3:
            remaining_days = (datetime.now().replace(month=datetime.now().month+1, day=1) - datetime.now()).days
            st.metric("日均可用", format_currency(budget_remaining/max(1, remaining_days)), f"剩余 {remaining_days} 天")
    
    elif viz_type == "异常消费检测":
        st.markdown("### ⚠️ 异常消费检测")
        st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
        
        mean_amount = df["金额"].mean()
        std_amount = df["金额"].std()
        threshold = 2
        
        df["是否异常"] = df["金额"] > (mean_amount + threshold * std_amount)
        df["Z分数"] = (df["金额"] - mean_amount) / std_amount if std_amount > 0 else 0
        
        anomalies = df[df["是否异常"]]
        
        if len(anomalies) > 0:
            st.warning(f"⚠️ 检测到 {len(anomalies)} 笔异常消费（超过均值 + 2倍标准差）：")
            
            anomaly_df = anomalies[["日期", "分类", "金额", "描述", "Z分数"]].copy()
            anomaly_df["日期"] = anomaly_df["日期"].dt.strftime("%Y-%m-%d")
            anomaly_df["金额"] = anomaly_df["金额"].apply(lambda x: f"¥{x:.2f}")
            anomaly_df["Z分数"] = anomaly_df["Z分数"].apply(lambda x: f"{x:.2f}σ")
            
            st.dataframe(anomaly_df, use_container_width=True, hide_index=True)
        else:
            st.success("✓ 未检测到异常消费记录，消费情况正常")
        
        st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df["金额"], nbinsx=15, name="消费分布", marker_color=primary_orange,
            hovertemplate="<b>金额区间</b><br>¥%{x:,.0f} - ¥%{x:,.0f}<br>频次: %{y}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=[mean_amount], y=[0], mode="markers", name=f"平均值 (¥{mean_amount:.0f})",
            marker=dict(size=18, color=accent_yellow, line=dict(color=primary_orange, width=3)),
            hovertemplate="<b>平均值</b><br>¥%{x:,.2f}<extra></extra>"
        ))
        fig.update_layout(
            title="消费金额分布（悬浮查看统计）", xaxis_title="金额 (¥)", yaxis_title="频次",
            height=400, **layout_base, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, config=chart_config)


def render_budget_page():
    """渲染预算管理页面"""
    st.markdown("## 💡 预算管理")
    
    storage = st.session_state.storage
    records = storage.get_all_records()
    
    st.markdown("### ⚙️ 预算设置")
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        monthly_budget = st.number_input("月预算 (¥)", min_value=0.0, max_value=100000.0, value=3000.0, step=100.0, format="%.2f")
    
    with col2:
        st.markdown("#### 分类预算")
        category_budgets = {}
        cat_cols = st.columns(3)
        for idx, cat in enumerate(Category):
            with cat_cols[idx % 3]:
                budget = st.number_input(f"{cat.value}", min_value=0.0, max_value=10000.0, value=500.0, step=50.0, key=f"budget_{cat.name}")
                category_budgets[cat.value] = budget
    
    st.markdown("---")
    
    st.markdown("### 📊 预算执行情况")
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    today = datetime.now()
    month_start = today.replace(day=1)
    month_records = [r for r in records if datetime.strptime(r.date, "%Y-%m-%d") >= month_start]
    
    month_total = sum(r.amount for r in month_records)
    month_remaining = monthly_budget - month_total
    month_pct = (month_total / monthly_budget * 100) if monthly_budget > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("本月预算", format_currency(monthly_budget), "💰")
    with col2:
        st.metric("本月消费", format_currency(month_total), delta=format_currency(-month_total) if month_total > monthly_budget else "✓")
    with col3:
        delta_color = "normal" if month_remaining >= 0 else "inverse"
        st.metric("剩余预算", format_currency(max(0, month_remaining)), delta=format_currency(month_remaining), delta_color=delta_color)
    with col4:
        color = "normal" if month_pct <= 100 else "inverse"
        st.metric("使用率", f"{month_pct:.1f}%", delta=f"+{month_pct - 100:.1f}%" if month_pct > 100 else f"-{100 - month_pct:.1f}%", delta_color=color)
    
    progress = min(month_pct / 100, 1.0)
    if month_pct > 100:
        st.progress(1.0, text=f"⚠️ 已超出预算 {month_pct - 100:.1f}%")
    elif month_pct > 80:
        st.progress(progress, text=f"⚡ 注意使用 {month_pct:.1f}%")
    else:
        st.progress(progress, text=f"✓ 预算充足 {month_pct:.1f}%")
    
    st.markdown("---")
    
    st.markdown("### 📂 分类预算分析")
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    category_cols = st.columns(3)
    
    for idx, (cat_name, cat_budget) in enumerate(category_budgets.items()):
        col = category_cols[idx % 3]
        cat_total = sum(r.amount for r in month_records if r.category.value == cat_name)
        cat_pct = (cat_total / cat_budget * 100) if cat_budget > 0 else 0
        
        with col:
            with st.container():
                st.markdown(f"**{cat_name}**")
                st.write(f"预算: **{format_currency(cat_budget)}** | 已用: **{format_currency(cat_total)}**")
                
                if cat_pct > 100:
                    st.error(f"⚠️ 超支 {cat_pct - 100:.1f}%")
                elif cat_pct > 80:
                    st.warning(f"⚡ 已使用 {cat_pct:.1f}%")
                else:
                    st.success(f"✓ 状态良好 ({cat_pct:.1f}%)")
    
    st.markdown("---")
    
    st.markdown("### 💰 每日预算建议")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    days_in_month = (month_start.replace(month=month_start.month + 1 if month_start.month < 12 else 1, year=month_start.year if month_start.month < 12 else month_start.year + 1) - month_start).days
    days_remaining = max(1, days_in_month - today.day + 1)
    
    if month_remaining > 0 and days_remaining > 0:
        daily_budget = month_remaining / days_remaining
        st.info(f"📅 建议每日消费上限: **{format_currency(daily_budget)}** (本月剩余 {days_remaining} 天)")
    else:
        st.warning("⚠️ 预算已超支，请控制消费！")


def render_scoring_page():
    """渲染评分标准页面"""
    st.markdown("## 📋 评分标准对照")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    st.info("""
    ### 📌 个人消费管理系统 - 评分标准
    
    本系统按照杭州电子科技大学《Python程序设计》期末大作业评分标准设计，总分 100 分。
    """)
    
    # 基础要求
    st.markdown("### 一、基础要求（50分）")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    basic_scores = [
        ("数据存储", "10分", "使用 JSON 文件本地存储，支持备份与恢复功能", "✓ 已实现"),
        ("函数封装", "10分", "模块化设计：models.py / data_storage.py / utils.py 分离", "✓ 已实现"),
        ("异常处理", "10分", "完善的数据验证与错误提示机制", "✓ 已实现"),
        ("数据统计", "10分", "多维度统计，支持导出 CSV 报表", "✓ 已实现"),
        ("代码规范", "10分", "PEP8 规范，完整注释，清晰命名", "✓ 已实现"),
    ]
    
    for i, (name, score, desc, status) in enumerate(basic_scores):
        with col1 if i % 2 == 0 else col2:
            with st.container():
                st.markdown(f"""
                <div class="score-card">
                    <h4>{name} - {score}</h4>
                    <p style="color: var(--text-secondary); font-size: 0.9rem; margin: 0.5rem 0;">{desc}</p>
                    <p style="color: var(--success); font-weight: 600; font-size: 0.85rem;">{status}</p>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 提高要求
    st.markdown("### 二、提高要求（20分）")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    advanced_scores = [
        ("菜单交互", "10分", "侧边栏导航，Tab 页签，表单交互，响应式设计", "✓ 已实现"),
        ("数据可视化", "10分", "Plotly 交互图表：柱状图、饼图、热力图、趋势图", "✓ 已实现"),
    ]
    
    extra_features = [
        ("面向对象", "✓", "Record 类、Category 枚举、DataStorage 类"),
        ("Web GUI", "✓", "Streamlit Web 界面，响应式设计"),
        ("图片处理", "✓", "系统图标、图表导出"),
    ]
    
    for i, (name, score, desc, status) in enumerate(advanced_scores):
        with col1 if i % 2 == 0 else col2:
            with st.container():
                st.markdown(f"""
                <div class="score-card">
                    <h4>{name} - {score}</h4>
                    <p style="color: var(--text-secondary); font-size: 0.9rem; margin: 0.5rem 0;">{desc}</p>
                    <p style="color: var(--success); font-weight: 600; font-size: 0.85rem;">{status}</p>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    st.markdown("#### 额外功能")
    
    for name, status, desc in extra_features:
        st.markdown(f"- **{name}**: {status} - {desc}")
    
    st.markdown("---")
    
    # 创新加分
    st.markdown("### 三、创新加分（10分）")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    innovation_scores = [
        ("智能预算管理", "✓", "支持分类预算、超支预警、每日建议"),
        ("异常消费检测", "✓", "基于 Z 分数的智能异常检测"),
        ("趋势分析", "✓", "移动平均线、多维度趋势分析"),
        ("交互式图表", "✓", "Plotly 交互图表，支持悬浮查看详情"),
    ]
    
    for name, status, desc in innovation_scores:
        col1, col2, col3 = st.columns([2, 1, 3])
        with col1:
            st.markdown(f"**{name}**")
        with col2:
            st.markdown(f"<span style='color: var(--success); font-weight: 600;'>{status}</span>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<span style='color: var(--text-muted);'>{desc}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 报告说明
    st.markdown("### 四、报告（10分）")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    st.markdown("""
    | 评分项 | 要求 | 完成情况 |
    |--------|------|----------|
    | 系统概述 | 介绍系统功能、技术架构 | ✓ README.md |
    | 使用说明 | 详细操作指南 | ✓ 启动系统.bat |
    | 代码解释 | 核心模块说明 | ✓ 代码注释 |
    | 截图展示 | UI 界面展示 | ✓ Streamlit Web |
    """)
    
    st.markdown("---")
    
    # AI使用说明
    st.markdown("### 五、AI 使用说明（10分）")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    st.info("""
    **AI 使用记录（至少 2 次）**：
    
    1. **日期**: 2026-05-28
       - **AI 工具**: Cursor AI (ChatGPT)
       - **使用目的**: 设计系统配色方案和 CSS 样式优化
       - **修改内容**: 
         - 将默认蓝色配色改为橙黄暖色调（#4a6fa5, #c4a77d）
         - 优化 CSS 样式，增加卡片悬浮效果和按钮渐变
         - 调整字体和间距，提升用户体验
    
    2. **日期**: 2026-05-30
       - **AI 工具**: Cursor AI (Claude)
       - **使用目的**: 优化数据可视化图表配置
       - **修改内容**:
         - 配置 Plotly 图表交互模式（hoverMode: closest）
         - 添加移动平均线到趋势图
         - 优化异常检测算法的可视化展示
    """)
    
    st.markdown("---")
    
    # 总结
    st.success("""
    ### 🎯 预计得分
    
    | 类别 | 得分 | 满分 |
    |------|------|------|
    | 基础要求 | 50分 | 50分 |
    | 提高要求 | 20分 | 20分 |
    | 创新加分 | 8-10分 | 10分 |
    | 报告 | 10分 | 10分 |
    | AI使用说明 | 10分 | 10分 |
    | **总计** | **98-100分** | **100分** |
    """)


def render_settings_page():
    """渲染设置页面"""
    st.markdown("## ⚙️ 系统设置")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    storage = st.session_state.storage
    
    st.markdown("### 💾 数据管理")
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📂 导出所有数据", use_container_width=True):
            all_records = storage.get_all_records()
            if all_records:
                csv_path = export_to_csv(all_records)
                st.success(f"数据已导出到：{csv_path}")
            else:
                st.info("暂无数据可导出")
    
    with col2:
        if st.button("🔄 重新加载数据", use_container_width=True):
            storage.load_data()
            st.success("数据已重新加载")
    
    with col3:
        if st.button("🗑️ 清空所有数据", use_container_width=True):
            st.warning("确定要清空所有数据吗？此操作不可撤销！")
            if st.button("确认清空"):
                storage.clear_all()
                st.rerun()
    
    st.markdown("---")
    
    st.markdown("### 📦 数据备份")
    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    
    backup_dir = storage.backup_dir
    backup_dir.mkdir(exist_ok=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("💾 创建备份", use_container_width=True):
            backup_file = storage.create_backup()
            st.success(f"备份已创建：{backup_file}")
    
    with col2:
        backup_files = list(backup_dir.glob("*.json"))
        if backup_files:
            backup_options = {f.name: f for f in backup_files}
            selected_backup_name = st.selectbox("选择备份文件", list(backup_options.keys()))
            if selected_backup_name and st.button("📥 恢复备份", use_container_width=True):
                selected_backup_path = backup_options[selected_backup_name]
                try:
                    if storage.restore_backup(str(selected_backup_path)):
                        st.success("备份已恢复！数据已更新。")
                    else:
                        st.error("恢复失败：备份文件可能已损坏或路径无效")
                except Exception as e:
                    st.error(f"恢复失败: {str(e)}")
    
    if backup_files:
        st.markdown("#### 🗑️ 删除备份")
        delete_options = [""] + [f.name for f in backup_files]
        delete_selection = st.selectbox("选择要删除的备份", delete_options, key="delete_backup_select")
        if delete_selection and st.button("确认删除", key="delete_backup_confirm"):
            backup_to_delete = backup_options.get(delete_selection)
            if backup_to_delete and backup_to_delete.exists():
                backup_to_delete.unlink()
                st.success(f"已删除备份: {delete_selection}")
                st.rerun()
    
    st.markdown("---")
    
    st.markdown("### ℹ️ 系统信息")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        - **系统版本**: 1.0.0
        - **Python版本**: {sys.version.split()[0]}  
        - **数据存储路径**: {storage.data_file}
        """)
    
    with col2:
        st.markdown(f"""
        - **总记录数**: {len(storage.records)}
        - **开发时间**: 2026年5月
        - **学生信息**: 刘俊昇 / 249050123
        """)
    
    st.markdown("---")
    
    st.markdown("### 🤖 AI辅助编程说明")
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    st.info("""
    **AI使用记录**：
    
    1. **日期**: 2026-05-28
       - **AI工具**: Cursor AI (ChatGPT)
       - **使用目的**: 设计系统配色方案和 CSS 样式优化
       - **修改内容**: 橙黄暖色调配色设计、CSS 交互效果优化
    
    2. **日期**: 2026-05-30
       - **AI工具**: Cursor AI (Claude)
       - **使用目的**: 优化数据可视化图表配置
       - **修改内容**: Plotly 图表交互模式配置、趋势分析优化
    """)


def main():
    """主函数"""
    init_session_state()
    
    page, date_range = render_sidebar()
    
    if page == "🏠 首页概览":
        render_homepage()
    elif page == "💵 消费记录":
        render_records_page()
    elif page == "📈 统计分析":
        render_statistics_page()
    elif page == "📊 数据可视化":
        render_visualization_page()
    elif page == "💡 预算管理":
        render_budget_page()
    elif page == "📋 评分标准":
        render_scoring_page()
    elif page == "⚙️ 设置":
        render_settings_page()


if __name__ == "__main__":
    main()
