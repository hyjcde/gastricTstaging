#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验室 GPU 预约表生成器 (专业版)
Laboratory GPU Reservation Schedule Generator (Professional Edition)

支持中英文双语
Supports both Chinese and English
"""

import pandas as pd
import xlsxwriter
from datetime import datetime, timedelta
import sys

# ================= 配置区域 =================
LANGUAGE = 'zh'  # 'zh' for Chinese, 'en' for English

DAYS_TO_GENERATE = 30  # 生成未来 30 天 / Generate next 30 days

GPU_LIST = ['GPU 0 (3090)', 'GPU 1 (3090)', 'GPU 2 (4090)', 'GPU 3 (A100)']  # 自定义你的显卡型号

TIME_SLOTS = [
    '09:00 - 14:00 (上午)',  # Chinese
    '14:00 - 20:00 (下午)',
    '20:00 - 09:00 (通宵)'
]

TIME_SLOTS_EN = [
    '09:00 - 14:00 (Morning)',
    '14:00 - 20:00 (Afternoon)',
    '20:00 - 09:00 (Overnight)'
]

# 下拉菜单选项 / Dropdown options
TASK_TYPES_ZH = ['模型训练', '数据处理', '代码调试', '推理测试', '长期占用(需审批)']
TASK_TYPES_EN = ['Model Training', 'Data Processing', 'Code Debugging', 'Inference Testing', 'Long-term Use (Approval Required)']

# ================= 多语言文本 =================
TEXTS = {
    'zh': {
        'file_name': '实验室GPU预约表_专业版.xlsx',
        'sheet_name': 'GPU预约',
        'date': '日期',
        'time_slot': '时间段',
        'task_type': '任务类型',
        'notes': '备注',
        'reserved_by': '预约人',
        'weekday_map': {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'},
        'success_msg': f"✅ 成功生成: ",
        'tip_msg': "提示: 上传到腾讯文档后，下拉菜单和条件格式通常都能完美保留。",
        'validation_title': '请选择类型',
        'validation_message': '请从下拉列表中选择任务类型'
    },
    'en': {
        'file_name': 'Lab_GPU_Reservation_Schedule_Pro.xlsx',
        'sheet_name': 'GPU Reservation',
        'date': 'Date',
        'time_slot': 'Time Slot',
        'task_type': 'Task Type',
        'notes': 'Notes',
        'reserved_by': 'Reserved By',
        'weekday_map': {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'},
        'success_msg': f"✅ Successfully generated: ",
        'tip_msg': "Tip: After uploading to Tencent Docs, dropdown menus and conditional formatting are usually preserved perfectly.",
        'validation_title': 'Please Select Type',
        'validation_message': 'Please select a task type from the dropdown list'
    }
}

# ================= 1. 数据生成逻辑 =================
def generate_schedule(language='zh'):
    """生成预约表数据"""
    texts = TEXTS[language]
    time_slots = TIME_SLOTS if language == 'zh' else TIME_SLOTS_EN
    task_types = TASK_TYPES_ZH if language == 'zh' else TASK_TYPES_EN
    
    data = []
    start_date = datetime.now().date()
    weekday_map = texts['weekday_map']
    
    for i in range(DAYS_TO_GENERATE):
        current_date = start_date + timedelta(days=i)
        weekday_num = current_date.weekday()
        
        if language == 'zh':
            date_str = f"{current_date.strftime('%m-%d')} ({weekday_map[weekday_num]})"
        else:
            date_str = f"{current_date.strftime('%m-%d')} ({weekday_map[weekday_num]})"
        
        is_weekend = weekday_num >= 5  # 判断是否为周末
        
        for slot in time_slots:
            row = {
                'raw_date': current_date,  # 用于后续逻辑判断，不写入Excel
                texts['date']: date_str,
                texts['time_slot']: slot,
                'is_weekend': is_weekend,  # 标记周末
                texts['reserved_by']: '',  # 留空给用户填
                texts['task_type']: '',  # 下拉菜单
                texts['notes']: ''
            }
            # 为每个 GPU 添加列
            for gpu in GPU_LIST:
                row[gpu] = ''
            
            data.append(row)
    
    return pd.DataFrame(data), texts, task_types, time_slots

# ================= 2. Excel 格式化与写入 =================
def create_excel(language='zh'):
    """创建格式化的 Excel 文件"""
    df, texts, task_types, time_slots = generate_schedule(language)
    
    # 定义列顺序：日期 | 时间段 | 预约人 | GPU列... | 任务类型 | 备注
    cols_order = [texts['date'], texts['time_slot'], texts['reserved_by']] + GPU_LIST + [texts['task_type'], texts['notes']]
    
    file_name = texts['file_name']
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')
    workbook = writer.book
    sheet_name = texts['sheet_name']
    
    # 先把 DataFrame 写入，但不包含 index，也不包含辅助列
    df[cols_order].to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    
    # --- 定义样式 (Styles) ---
    # 1. 表头样式：深蓝底白字，加粗，居中
    header_fmt = workbook.add_format({
        'bold': True, 'font_color': 'white', 'bg_color': '#2F5597',
        'align': 'center', 'valign': 'vcenter', 'border': 1
    })
    
    # 2. 普通单元格：居中，细边框
    normal_fmt = workbook.add_format({
        'align': 'center', 'valign': 'vcenter', 'border': 1
    })
    
    # 3. 周末样式：浅灰色背景 (用于日期列)
    weekend_fmt = workbook.add_format({
        'align': 'center', 'valign': 'vcenter', 'border': 1,
        'bg_color': '#E7E6E6', 'font_color': '#595959'
    })
    
    # 4. 占用样式 (条件格式用)：浅绿色背景，深绿字
    occupied_fmt = workbook.add_format({
        'bg_color': '#C6EFCE', 'font_color': '#006100',
        'align': 'center', 'valign': 'vcenter', 'border': 1
    })
    
    # 5. 隔行变色样式（浅蓝）
    alternate_fmt = workbook.add_format({
        'align': 'center', 'valign': 'vcenter', 'border': 1,
        'bg_color': '#F0F8FF'
    })
    
    # --- 应用列宽与格式 ---
    # 设置列宽 (根据内容调整)
    worksheet.set_column('A:A', 15)  # 日期
    worksheet.set_column('B:B', 20)  # 时间段
    worksheet.set_column('C:C', 12, normal_fmt)  # 预约人
    
    # GPU 列宽
    first_gpu_col_idx = 3  # 预约人列在索引2，GPU从索引3开始
    last_gpu_col_idx = 3 + len(GPU_LIST) - 1
    worksheet.set_column(first_gpu_col_idx, last_gpu_col_idx, 18, normal_fmt)
    
    # 任务类型和备注
    task_col_idx = last_gpu_col_idx + 1
    notes_col_idx = last_gpu_col_idx + 2
    worksheet.set_column(task_col_idx, task_col_idx, 15, normal_fmt)  # 任务类型
    worksheet.set_column(notes_col_idx, notes_col_idx, 30, normal_fmt)  # 备注
    
    # --- 重写表头 (应用样式) ---
    for col_num, value in enumerate(cols_order):
        worksheet.write(0, col_num, value, header_fmt)
    
    # --- 逐行处理 (处理周末高亮和隔行变色) ---
    for row_idx, row_data in df.iterrows():
        excel_row = row_idx + 1  # Excel从1开始(0是表头)
        
        # 判断是否为周末
        is_weekend = row_data['is_weekend']
        # 判断是否为偶数行（用于隔行变色）
        is_even_row = (row_idx % 2 == 0)
        
        # 日期和时间段样式
        if is_weekend:
            date_fmt = weekend_fmt
        elif is_even_row:
            date_fmt = alternate_fmt
        else:
            date_fmt = normal_fmt
        
        # 写入日期和时间段，应用样式
        worksheet.write(excel_row, 0, row_data[texts['date']], date_fmt)
        worksheet.write(excel_row, 1, row_data[texts['time_slot']], date_fmt)
        
        # 预约人列应用隔行变色
        reserved_by_fmt = alternate_fmt if is_even_row else normal_fmt
        worksheet.write(excel_row, 2, row_data[texts['reserved_by']], reserved_by_fmt)
        
        # GPU 列应用隔行变色（但会被条件格式覆盖）
        gpu_fmt = alternate_fmt if is_even_row else normal_fmt
        for gpu_col in range(first_gpu_col_idx, last_gpu_col_idx + 1):
            # 先写入格式，条件格式会在有内容时覆盖
            worksheet.write(excel_row, gpu_col, row_data[GPU_LIST[gpu_col - first_gpu_col_idx]], gpu_fmt)
        
        # 任务类型和备注列应用隔行变色
        task_fmt = alternate_fmt if is_even_row else normal_fmt
        worksheet.write(excel_row, task_col_idx, row_data[texts['task_type']], task_fmt)
        worksheet.write(excel_row, notes_col_idx, row_data[texts['notes']], task_fmt)
    
    # --- 高级功能 1: 冻结窗格 ---
    # 冻结第一行(表头) 和 前三列(日期、时间、预约人)
    worksheet.freeze_panes(1, 3)
    
    # --- 高级功能 2: 数据验证 (下拉菜单) ---
    # 在 "任务类型" 列添加下拉菜单
    # 应用范围：从第2行到最后一行
    worksheet.data_validation(1, task_col_idx, len(df), task_col_idx, {
        'validate': 'list',
        'source': task_types,
        'input_title': texts['validation_title'],
        'input_message': texts['validation_message']
    })
    
    # --- 高级功能 3: 条件格式 (Visual Cues) ---
    # 如果 GPU 这一栏被填了内容 (不为空)，自动变绿
    # 范围：所有 GPU 列
    worksheet.conditional_format(1, first_gpu_col_idx, len(df), last_gpu_col_idx, {
        'type': 'no_blanks',
        'format': occupied_fmt
    })
    
    # 预约人列也添加条件格式（如果填了名字变绿）
    reserved_by_col_idx = 2  # 预约人列在第三列（索引2）
    worksheet.conditional_format(1, reserved_by_col_idx, len(df), reserved_by_col_idx, {
        'type': 'no_blanks',
        'format': occupied_fmt
    })
    
    writer.close()
    
    print(f"{texts['success_msg']}{file_name}")
    print(texts['tip_msg'])
    return file_name

# ================= 主程序 =================
if __name__ == '__main__':
    # 支持命令行参数选择语言
    if len(sys.argv) > 1:
        lang = sys.argv[1].lower()
        if lang in ['zh', 'en', 'chinese', 'english']:
            LANGUAGE = 'zh' if lang in ['zh', 'chinese'] else 'en'
        else:
            print("Usage: python generate_gpu_schedule.py [zh|en]")
            print("Default: Chinese (zh)")
            LANGUAGE = 'zh'
    else:
        # 默认生成中英文两个版本
        print("Generating both Chinese and English versions...")
        create_excel('zh')
        create_excel('en')
        print("\n✅ Both versions generated successfully!")
        sys.exit(0)
    
    create_excel(LANGUAGE)

