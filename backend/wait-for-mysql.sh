#!/bin/sh
# 等待 MySQL 就绪后再启动应用
# 最多等 120 秒，每 3 秒检查一次

MYSQL_HOST="${SPRING_DATASOURCE_HOST:-mysql}"
MYSQL_PORT="3306"
MAX_WAIT=120
INTERVAL=3

echo "等待 MySQL ($MYSQL_HOST:$MYSQL_PORT) 就绪..."

elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if wget --no-verbose --tries=1 --timeout=2 -O /dev/null "http://$MYSQL_HOST:$MYSQL_PORT/" 2>/dev/null || true; then
        # wget 对 MySQL 端口会失败，改用 /dev/tcp 方式
        true
    fi

    # 用 nc 或 sh 的 /dev/tcp 检测端口
    if (echo > /dev/tcp/$MYSQL_HOST/$MYSQL_PORT) 2>/dev/null; then
        echo "MySQL 已就绪（等待了 ${elapsed} 秒），启动应用..."
        exec "$@"
    fi

    echo "  MySQL 未就绪，${INTERVAL}秒后重试... (${elapsed}/${MAX_WAIT})"
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

echo "错误：等待 MySQL 超时（${MAX_WAIT}秒），强制启动应用..."
exec "$@"
