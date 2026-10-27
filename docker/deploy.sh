#!/bin/bash
set -e

APP_DIR="/opt/hr-system"
COMPOSE_DIR="$APP_DIR"
BACKUP_DIR="$APP_DIR/docker/backups"
HEALTH_URL="http://localhost/api/actuator/health"

echo "=========================================="
echo "  HR 员工管理系统 — 生产部署脚本"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

cd "$COMPOSE_DIR"

echo ""
echo "[1/6] 拉取最新代码..."
git pull origin main

echo ""
echo "[2/6] 备份当前运行配置..."
mkdir -p "$BACKUP_DIR"
cp docker-compose.yml "$BACKUP_DIR/docker-compose.yml.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true

echo ""
echo "[3/6] 拉取基础镜像..."
docker compose pull mysql redis frontend 2>/dev/null || true

echo ""
echo "[4/6] 构建并启动服务..."
docker compose up -d --build

echo ""
echo "[5/6] 清理无用镜像..."
docker image prune -f

echo ""
echo "[6/6] 健康检查..."
for i in $(seq 1 15); do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        echo "  后端健康检查通过"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "  警告: 后端健康检查未通过，请手动检查"
        docker compose ps
        docker compose logs --tail=30 backend
        exit 1
    fi
    echo "  等待后端启动... ($i/15)"
    sleep 5
done

echo ""
echo "=========================================="
echo "  部署成功"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
docker compose ps
