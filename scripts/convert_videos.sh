#!/bin/bash
# 批量转换 WMV 视频为 MP4 格式
# 使用方法: ./convert_videos.sh

set -e

VIDEO_ROOT="/Users/huangyijun/Projects/胃癌T分期/胃癌视频"
OUTPUT_ROOT="/Users/huangyijun/Projects/胃癌T分期/gastric-scan-next/public/videos"

# 创建输出目录
mkdir -p "$OUTPUT_ROOT/direct_surgery"
mkdir -p "$OUTPUT_ROOT/neoadjuvant"

# 计数器
total=0
converted=0
skipped=0
failed=0

# 转换函数
convert_video() {
    local input_file="$1"
    local output_file="$2"
    
    if [ -f "$output_file" ]; then
        echo "⏭️  跳过 (已存在): $(basename "$output_file")"
        ((skipped++))
        return 0
    fi
    
    echo "🔄 转换中: $(basename "$input_file")"
    
    if ffmpeg -i "$input_file" \
        -c:v libx264 \
        -preset fast \
        -crf 23 \
        -c:a aac \
        -b:a 128k \
        -movflags +faststart \
        -y \
        -loglevel error \
        "$output_file" 2>/dev/null; then
        echo "✅ 完成: $(basename "$output_file")"
        ((converted++))
    else
        echo "❌ 失败: $(basename "$input_file")"
        ((failed++))
    fi
}

echo "=========================================="
echo "🎬 胃癌超声视频批量转码工具"
echo "=========================================="
echo "输入目录: $VIDEO_ROOT"
echo "输出目录: $OUTPUT_ROOT"
echo ""

# 处理直接手术组
echo "📁 处理: 直接手术"
echo "------------------------------------------"
for wmv_file in "$VIDEO_ROOT/直接手术"/*.wmv; do
    if [ -f "$wmv_file" ]; then
        ((total++))
        filename=$(basename "$wmv_file" .wmv)
        output_file="$OUTPUT_ROOT/direct_surgery/${filename}.mp4"
        convert_video "$wmv_file" "$output_file"
    fi
done

# 处理直接手术/喝水子目录
if [ -d "$VIDEO_ROOT/直接手术/喝水" ]; then
    mkdir -p "$OUTPUT_ROOT/direct_surgery/water_filled"
    echo ""
    echo "📁 处理: 直接手术/喝水"
    echo "------------------------------------------"
    for wmv_file in "$VIDEO_ROOT/直接手术/喝水"/*.wmv; do
        if [ -f "$wmv_file" ]; then
            ((total++))
            filename=$(basename "$wmv_file" .wmv)
            output_file="$OUTPUT_ROOT/direct_surgery/water_filled/${filename}.mp4"
            convert_video "$wmv_file" "$output_file"
        fi
    done
fi

# 处理新辅助治疗组
echo ""
echo "📁 处理: 新辅助治疗"
echo "------------------------------------------"
for wmv_file in "$VIDEO_ROOT/新辅助治疗"/*.wmv; do
    if [ -f "$wmv_file" ]; then
        ((total++))
        filename=$(basename "$wmv_file" .wmv)
        output_file="$OUTPUT_ROOT/neoadjuvant/${filename}.mp4"
        convert_video "$wmv_file" "$output_file"
    fi
done

# 处理新辅助治疗/喝水子目录
if [ -d "$VIDEO_ROOT/新辅助治疗/喝水" ]; then
    mkdir -p "$OUTPUT_ROOT/neoadjuvant/water_filled"
    echo ""
    echo "📁 处理: 新辅助治疗/喝水"
    echo "------------------------------------------"
    for wmv_file in "$VIDEO_ROOT/新辅助治疗/喝水"/*.wmv; do
        if [ -f "$wmv_file" ]; then
            ((total++))
            filename=$(basename "$wmv_file" .wmv)
            output_file="$OUTPUT_ROOT/neoadjuvant/water_filled/${filename}.mp4"
            convert_video "$wmv_file" "$output_file"
        fi
    done
fi

echo ""
echo "=========================================="
echo "📊 转码统计"
echo "=========================================="
echo "总计: $total 个视频"
echo "✅ 成功转换: $converted"
echo "⏭️  已跳过: $skipped"
echo "❌ 失败: $failed"
echo "=========================================="

