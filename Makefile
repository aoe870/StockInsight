# StockInsight Makefile
# 用于构建和管理 SAPAS 股票分析平台镜像

# 配置
DOCKER_USER ?= stockinsight
IMAGE_TAG ?= latest
COMPOSE_FILE = sapas/docker-compose.yml

# 颜色输出
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help build push build-gateway build-backend build-frontend

# 默认目标
.DEFAULT_GOAL := help

# 帮助信息
help:
	@echo "$(BLUE)StockInsight - SAPAS 股票分析平台$(NC)"
	@echo ""
	@echo "$(GREEN)可用命令:$(NC)"
	@echo "  make build           构建所有镜像"
	@echo "  make build-gateway  构建数据网关镜像"
	@echo "  make build-backend   构建后端镜像"
	@echo "  make build-frontend  构建前端镜像"
	@echo "  make push            推送所有镜像"
	@echo "  make push-gateway   推送数据网关镜像"
	@echo "  make push-backend    推送后端镜像"
	@echo "  make push-frontend  推送前端镜像"
	@echo ""
	@echo "$(YELLOW)示例:$(NC)"
	@echo "  make build IMAGE_TAG=v1.0.0            # 构建指定版本"
	@echo "  make push DOCKER_USER=yourname             # 推送到指定账号"
	@echo ""
	@echo "$(YELLOW)使用脚本:$(NC)"
	@echo "  ./init-deploy.sh      # 初始化部署（含数据库初始化）"
	@echo "  ./start.sh           # 启动服务（不构建镜像）"
	@echo "  ./stop.sh            # 停止服务"

# 构建所有镜像
build: build-gateway build-backend build-frontend

# 构建数据网关镜像
build-gateway:
	@echo "$(BLUE)构建数据网关镜像...$(NC)"
	docker build -t $(DOCKER_USER)/data-gateway:$(IMAGE_TAG) -f data_gateway/Dockerfile data_gateway
	@echo "$(GREEN)数据网关镜像构建完成: $(DOCKER_USER)/data-gateway:$(IMAGE_TAG)$(NC)"

# 构建后端镜像
build-backend:
	@echo "$(BLUE)构建后端镜像...$(NC)"
	docker build -t $(DOCKER_USER)/sapas-backend:$(IMAGE_TAG) -f sapas/backend/Dockerfile sapas/backend
	@echo "$(GREEN)后端镜像构建完成: $(DOCKER_USER)/sapas-backend:$(IMAGE_TAG)$(NC)"

# 构建前端镜像
build-frontend:
	@echo "$(BLUE)构建前端镜像...$(NC)"
	docker build -t $(DOCKER_USER)/sapas-frontend:$(IMAGE_TAG) -f sapas/frontend/Dockerfile sapas/frontend
	@echo "$(GREEN)前端镜像构建完成: $(DOCKER_USER)/sapas-frontend:$(IMAGE_TAG)$(NC)"

# 推送所有镜像
push: push-gateway push-backend push-frontend

# 推送数据网关镜像
push-gateway:
	@echo "$(BLUE)推送数据网关镜像...$(NC)"
	docker push $(DOCKER_USER)/data-gateway:$(IMAGE_TAG)
	@echo "$(GREEN)数据网关镜像推送完成$(NC)"

# 推送后端镜像
push-backend:
	@echo "$(BLUE)推送后端镜像...$(NC)"
	docker push $(DOCKER_USER)/sapas-backend:$(IMAGE_TAG)
	@echo "$(GREEN)后端镜像推送完成$(NC)"

# 推送前端镜像
push-frontend:
	@echo "$(BLUE)推送前端镜像...$(NC)"
	docker push $(DOCKER_USER)/sapas-frontend:$(IMAGE_TAG)
	@echo "$(GREEN)前端镜像推送完成$(NC)"
