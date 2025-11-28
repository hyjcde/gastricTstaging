# GPU 预约表生成器使用说明

## 功能特点

### ✨ 核心功能
1. **智能日期处理**：自动标记周末（周六周日背景变灰）
2. **数据验证**：任务类型列支持下拉菜单选择
3. **自动变色**：填写预约人/GPU后自动变绿
4. **隔行变色**：不同行使用不同背景色，视觉清晰
5. **冻结窗格**：固定表头和日期列，方便查看

### 🌍 多语言支持
- 中文版：`实验室GPU预约表_专业版.xlsx`
- 英文版：`Lab_GPU_Reservation_Schedule_Pro.xlsx`

## 安装依赖

```bash
pip install pandas xlsxwriter
```

## 使用方法

### 方法 1：生成中英文两个版本（推荐）
```bash
python scripts/generate_gpu_schedule.py
```
默认会同时生成中文版和英文版两个文件。

### 方法 2：只生成中文版
```bash
python scripts/generate_gpu_schedule.py zh
```

### 方法 3：只生成英文版
```bash
python scripts/generate_gpu_schedule.py en
```

## 自定义配置

编辑 `generate_gpu_schedule.py` 文件中的配置区域：

```python
# 生成天数
DAYS_TO_GENERATE = 30  # 修改为你需要的天数

# GPU 列表
GPU_LIST = ['GPU 0 (3090)', 'GPU 1 (3090)', 'GPU 2 (4090)', 'GPU 3 (A100)']

# 时间段（中文）
TIME_SLOTS = [
    '09:00 - 14:00 (上午)',
    '14:00 - 20:00 (下午)',
    '20:00 - 09:00 (通宵)'
]

# 时间段（英文）
TIME_SLOTS_EN = [
    '09:00 - 14:00 (Morning)',
    '14:00 - 20:00 (Afternoon)',
    '20:00 - 09:00 (Overnight)'
]

# 任务类型选项
TASK_TYPES_ZH = ['模型训练', '数据处理', '代码调试', '推理测试', '长期占用(需审批)']
TASK_TYPES_EN = ['Model Training', 'Data Processing', 'Code Debugging', 'Inference Testing', 'Long-term Use (Approval Required)']
```

## 生成的表格结构

### 列结构
1. **日期** (Date)：格式为 `MM-DD (星期X)`
2. **时间段** (Time Slot)：三个时间段选择
3. **预约人** (Reserved By)：填写预约者姓名
4. **GPU 0-3**：四个 GPU 列，填写使用人
5. **任务类型** (Task Type)：下拉菜单选择
6. **备注** (Notes)：自由文本

### 视觉特性
- **周末标记**：周六周日的日期列背景为灰色
- **自动变绿**：填写预约人或 GPU 后，单元格自动变为浅绿色
- **隔行变色**：偶数行使用浅蓝色背景，提高可读性
- **冻结窗格**：滚动时前3列（日期、时间段、预约人）保持固定

## 上传到腾讯文档后的建议

1. **保护表头**：
   - 选中第一行
   - 右键 -> `保护范围` -> 设置为 `仅我可编辑`

2. **定期更新**：
   - 每月重新运行脚本生成新的30天表格
   - 或手动删除过期日期，添加新日期

3. **权限管理**：
   - 设置合适的编辑权限
   - 建议设置为"所有人可编辑"，但保护表头

## 故障排除

### 问题：导入错误 `ModuleNotFoundError: No module named 'pandas'`
**解决**：安装依赖
```bash
pip install pandas xlsxwriter
```

### 问题：生成的 Excel 文件打不开
**解决**：确保使用 `xlsxwriter` 引擎，不要使用 `openpyxl`

### 问题：下拉菜单在腾讯文档中不显示
**解决**：腾讯文档可能不完全支持 Excel 的数据验证功能，但条件格式（自动变色）通常可以正常显示

## 示例输出

生成的文件包含：
- ✅ 30天的预约表格
- ✅ 每天3个时间段
- ✅ 4个 GPU 列
- ✅ 周末自动标记
- ✅ 下拉菜单（任务类型）
- ✅ 条件格式（自动变色）
- ✅ 冻结窗格
- ✅ 隔行变色

## 技术支持

如有问题，请检查：
1. Python 版本 >= 3.6
2. 已安装所有依赖
3. 文件路径正确
4. 有写入权限

