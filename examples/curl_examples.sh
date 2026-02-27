#!/bin/bash
# cURL 请求示例 - 数据源调研平台 API

BASE_URL="http://localhost:8000"

echo "========================================="
echo "数据源调研平台 API - cURL 示例"
echo "========================================="
echo ""

# 1. 健康检查
echo "1. 健康检查"
echo "   GET /health"
curl -s "${BASE_URL}/health" | jq .
echo ""

# 2. 启动调研任务
echo "2. 启动调研任务"
echo "   POST /api/research"
TASK_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/research" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "找科技媒体的数据源，需要包含标题、作者、发布时间"
  }')
echo "$TASK_RESPONSE" | jq .

# 提取任务 ID
TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.task_id')
echo "   任务 ID: $TASK_ID"
echo ""

# 3. 获取任务状态
echo "3. 获取任务状态"
echo "   GET /api/research/${TASK_ID}/status"
curl -s "${BASE_URL}/api/research/${TASK_ID}/status" | jq .
echo ""

# 4. 获取任务结果（需要等待任务完成）
echo "4. 获取任务结果（需要等待任务完成）"
echo "   GET /api/research/${TASK_ID}/result"
echo "   注意: 如果任务未完成，会返回 404"
curl -s "${BASE_URL}/api/research/${TASK_ID}/result" | jq .
echo ""

# 5. SSE 进度流（在新终端中运行）
echo "5. SSE 进度流（在新终端中运行）"
echo "   GET /api/research/${TASK_ID}/progress"
echo "   命令:"
echo "   curl -N -H 'Accept: text/event-stream' \"${BASE_URL}/api/research/${TASK_ID}/progress\""
echo ""

echo "========================================="
echo "示例完成"
echo "========================================="
