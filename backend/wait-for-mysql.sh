#!/bin/sh
# 等待 MySQL 就绪后再启动应用
# 检测端口 + 等待 MySQL 完全初始化

MYSQL_HOST="${SPRING_DATASOURCE_HOST:-mysql}"
MYSQL_PORT="3306"
MAX_WAIT=120
INTERVAL=3

echo "========================================="
echo "  等待 MySQL ($MYSQL_HOST:$MYSQL_PORT)..."
echo "========================================="

elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if (echo > /dev/tcp/$MYSQL_HOST/$MYSQL_PORT) 2>/dev/null; then
        echo "  MySQL 端口已开放，等待 5 秒确保初始化完成..."
        sleep 5
        echo "MySQL 就绪（等待了 ${elapsed} 秒），启动应用..."
        exec "$@"
    fi

    echo "  MySQL 未就绪，${INTERVAL}秒后重试... (${elapsed}/${MAX_WAIT})"
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

echo "警告：等待 MySQL 超时（${MAX_WAIT}秒），尝试启动应用..."
exec "$@"
