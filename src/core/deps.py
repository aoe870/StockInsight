"""
FastAPI 依赖项
提供认证、权限等依赖注入
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.auth import auth_service
from src.models.user import User
from src.utils.logger import logger

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """当前用户信息"""
    def __init__(self, user_id: UUID, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role
    
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """
    获取当前用户（可选）
    如果没有提供令牌或令牌无效，返回None
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    
    if payload is None:
        return None
    
    try:
        user_id = UUID(payload.get("sub"))
        username = payload.get("username")
        role = payload.get("role", "user")
        return CurrentUser(user_id=user_id, username=username, role=role)
    except (ValueError, TypeError):
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """
    获取当前用户（必需）
    如果没有提供令牌或令牌无效，抛出401异常
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(payload.get("sub"))
        username = payload.get("username")
        role = payload.get("role", "user")
        return CurrentUser(user_id=user_id, username=username, role=role)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前活跃用户的完整信息
    会从数据库查询用户详情
    """
    user = await auth_service.get_user_by_id(db, current_user.user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    
    return user


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    要求管理员权限
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user

