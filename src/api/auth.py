"""
认证 API 路由
提供登录、注册、用户信息等接口
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user, get_current_active_user, CurrentUser
from src.services.auth import auth_service
from src.models.user import User
from src.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["认证"])


# ==================== 请求/响应模型 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class UserInfo(BaseModel):
    """用户信息"""
    id: str
    username: str
    email: Optional[str]
    nickname: Optional[str]
    avatar: Optional[str]
    role: str
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """更新个人信息请求"""
    nickname: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    avatar: Optional[str] = Field(None, max_length=255)


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)


# ==================== API 接口 ====================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    user = await auth_service.authenticate_user(db, request.username, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 更新最后登录时间
    user.last_login_at = datetime.now()
    await db.commit()

    # 生成令牌
    access_token = auth_service.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )

    logger.info(f"用户登录成功: {user.username}")

    return TokenResponse(
        access_token=access_token,
        expires_in=auth_service.expire_minutes * 60,
        user=UserInfo(
            id=str(user.id),
            username=user.username,
            email=user.email,
            nickname=user.nickname,
            avatar=user.avatar,
            role=user.role,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = await auth_service.get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 创建用户
    user = User(
        username=request.username,
        password_hash=auth_service.hash_password(request.password),
        email=request.email,
        nickname=request.nickname or request.username,
        role="user",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 生成令牌
    access_token = auth_service.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )

    logger.info(f"新用户注册: {user.username}")

    return TokenResponse(
        access_token=access_token,
        expires_in=auth_service.expire_minutes * 60,
        user=UserInfo(
            id=str(user.id),
            username=user.username,
            email=user.email,
            nickname=user.nickname,
            avatar=user.avatar,
            role=user.role,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return UserInfo(
        id=str(user.id),
        username=user.username,
        email=user.email,
        nickname=user.nickname,
        avatar=user.avatar,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.put("/profile", response_model=UserInfo)
async def update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新个人信息"""
    if request.nickname is not None:
        user.nickname = request.nickname
    if request.email is not None:
        user.email = request.email
    if request.avatar is not None:
        user.avatar = request.avatar

    await db.commit()
    await db.refresh(user)

    logger.info(f"用户更新资料: {user.username}")

    return UserInfo(
        id=str(user.id),
        username=user.username,
        email=user.email,
        nickname=user.nickname,
        avatar=user.avatar,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not auth_service.verify_password(request.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    # 更新密码
    user.password_hash = auth_service.hash_password(request.new_password)
    await db.commit()

    logger.info(f"用户修改密码: {user.username}")

    return {"success": True, "message": "密码修改成功"}


@router.post("/logout")
async def logout(
    current_user: CurrentUser = Depends(get_current_user)
):
    """用户登出（客户端需要删除token）"""
    logger.info(f"用户登出: {current_user.username}")
    return {"success": True, "message": "登出成功"}
