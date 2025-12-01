#!/bin/bash

# Load Test Script for Kubernetes HPA Demonstration
# 作者：Gemini
# 描述：模拟大量并发请求以提高 API Gateway 的 CPU 利用率，从而触发 HPA 伸缩。
# --------------------------------------------------------------------------------------

# !!! 必填项 !!!
# 将 YOUR_EXTERNAL_IP 替换为您的 api-gateway-external Service 的外部 IP 地址
# 您可以通过以下命令获取：
# kubectl get svc api-gateway-external -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
EXTERNAL_IP=34.60.118.29 
echo "Using EXTERNAL_IP: $EXTERNAL_IP"
API_ENDPOINT="/data_entry_web" # 目标 API 路径，会由 API Gateway 代理到 data-entry-web
TOTAL_CONCURRENCY=500          # 模拟同时运行的请求总数
DURATION_SECONDS=120           # 负载测试持续时间（秒）

# --------------------------------------------------------------------------------------

TARGET_URL="http://${EXTERNAL_IP}${API_ENDPOINT}"
PID_FILE="load_test_pids.txt"

# 1. 定义发送单个请求的函数
send_request() {
    # -s: 静默模式
    # -o /dev/null: 丢弃输出内容
    # -w "%{http_code}": 打印 HTTP 状态码
    # 我们调用的是一个 GET 页面，所以这里是 GET 请求
    curl -s -o /dev/null -w "%{http_code}" "${TARGET_URL}"
    # 随机暂停一段时间，模拟真实用户行为
    sleep $(echo "scale=2; rand() * 0.5" | bc -l) 
}

# 2. 清理先前运行的后台进程
cleanup() {
    echo "停止所有后台进程..."
    if [ -f "$PID_FILE" ]; then
        # 尝试杀死所有记录的进程 ID
        cat "$PID_FILE" | xargs -r kill
        rm "$PID_FILE"
    fi
    echo "负载测试清理完成。"
    # 确保在脚本退出时清理
    exit 0
}

# 设置 trap，确保脚本被中断（Ctrl+C）时，后台进程也能被终止
trap cleanup INT TERM

echo "----------------------------------------------------"
echo "开始负载测试： ${TOTAL_CONCURRENCY} 个并发请求，持续 ${DURATION_SECONDS} 秒..."
echo "目标 URL: ${TARGET_URL}"
echo "----------------------------------------------------"

# 清空 PID 文件
> "$PID_FILE"

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION_SECONDS))

# 3. 启动并发进程
for i in $(seq 1 $TOTAL_CONCURRENCY); do
    # 使用 while 循环让每个进程持续发送请求，直到时间结束
    (
        while [ $(date +%s) -lt $END_TIME ]; do
            send_request
            # 打印一个点来表示活动
            echo -n "."
        done
    ) &
    # 记录后台进程的 PID，以便稍后清理
    echo $! >> "$PID_FILE"
done

echo ""
echo "所有 ${TOTAL_CONCURRENCY} 个并发进程已启动。"
echo "请等待 ${DURATION_SECONDS} 秒，观察 HPA 的效果..."

# 4. 等待测试结束
wait $! 2>/dev/null 

# 5. 测试结束，执行清理
cleanup