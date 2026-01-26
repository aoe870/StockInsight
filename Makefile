# StockInsight Makefile
# 用于构建和推送 Docker 镜像

# 配置
DOCKER_USER ?= monstertop
IMAGE_NAME = data-gateway
IMAGE_TAG ?= latest
FULL_IMAGE = $(DOCKER_USER)/$(IMAGE_NAME):$(IMAGE_TAG)

# 颜色输出
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

.PHONY: help build push login clean

# 默认目标
.DEFAULT_GOAL := help

help:
	@echo "$(BLUE)StockInsight Docker 镜像管理$(NC)"
	@echo ""
	@echo "$(GREEN)可用命令:$(NC)"
	@echo "  make build          构建镜像 ($(FULL_IMAGE))"
	@echo "  make push           推送镜像到 Docker Hub"
	@echo "  make build-push     构建并推送镜像"
	@echo "  make login          登录 Docker Hub"
	@echo "  make clean          清理未使用的镜像和容器"
	@echo "  make tag VERSION=1.0.0  打标签版本"
	@echo ""
	@echo "$(YELLOW)示例:$(NC)"
	@echo "  make build                          # 构建默认镜像"
	@echo "  make build IMAGE_TAG=v1.0.0       # 构建指定版本"
	@echo "  make push DOCKER_USER=username       # 推送到指定账号"
	@echo "  make build-push IMAGE_TAG=v1.0.0   # 构建并推送 v1.0.0"

build:
	@echo "$(BLUE)开始构建镜像: $(FULL_IMAGE)$(NC)"
	docker build -t $(FULL_IMAGE) -f Dockerfile .
	@echo "$(GREEN)构建完成: $(FULL_IMAGE)$(NC)"

push:
	@echo "$(BLUE)推送镜像到 Docker Hub: $(FULL_IMAGE)$(NC)"
	@echo "$(YELLOW)请先确保已登录: docker login$(NC)"
	docker push $(FULL_IMAGE)
	@echo "$(GREEN)推送完成: $(FULL_IMAGE)$(NC)"

build-push: build
	@echo "$(BLUE)开始推送镜像: $(FULL_IMAGE)$(NC)"
	docker push $(FULL_IMAGE)
	@echo "$(GREEN)构建和推送完成: $(FULL_IMAGE)$(NC)"

login:
	docker login

tag:
	@echo "$(BLUE)给镜像打标签$(NC)"
	docker tag $(DOCKER_USER)/$(IMAGE_NAME):$(IMAGE_TAG) $(DOCKER_USER)/$(IMAGE_NAME):$(VERSION)
	@echo "$(GREEN)标签完成: $(DOCKER_USER)/$(IMAGE_NAME):$(VERSION)$(NC)"

clean:
	@echo "$(BLUE)清理未使用的镜像和容器$(NC)"
	docker system prune -f
	@echo "$(GREEN)清理完成$(NC)"
