"""
认证相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.database import get_db_session
from ..core.auth import AuthService
from ..schemas.user import UserLogin, UserRegister, TokenResponse, UserResponse, UserUpdate, ChangePassword
from ..models import User, UserRole

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/register", response_model=dict)
async def register(
    request: UserRegister,
    db: AsyncSession = Depends(get_db_session)
):
    """
    用户注册

    请求示例:
    ```json
    {
      "username": "admin",
      "password": "admin123",
      "password_confirm": "admin123",
      "email": "admin@example.com",
      "nickname": "管理员"
    }
    ```
    """
    # 验证密码确认
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的密码不一致"
        )

    # 检查用户名是否已存在
    existing_user = await AuthService.get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被使用"
        )

    # 创建用户
    hashed_password = AuthService.get_password_hash(request.password)

    user = User(
        username=request.username,
        password_hash=hashed_password,
        email=request.email,
        nickname=request.nickname,
        role=UserRole.USER
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 返回用户信息
    return {
        "code": 0,
        "message": "注册成功",
        "data": UserResponse.model_validate(user)
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLogin,
    db: AsyncSession = Depends(get_db_session)
):
    """
    用户登录

    请求示例:
    ```json
    {
      "username": "admin",
      "password": "admin123",
      "remember_me": true
    }
    ```
    """
    # 查找用户
    user = await AuthService.get_user_by_username(db, request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not AuthService.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    # 更新最后登录时间
    from datetime import datetime
    user.last_login_at = datetime.utcnow()

    # 生成令牌
    access_token, access_expires = AuthService.create_access_token(
        {"sub": str(user.id), "type": "access"}
    )
    refresh_token = AuthService.create_refresh_token({"sub": str(user.id), "type": "refresh"})

    await db.commit()

    return TokenResponse(
        code=0,
        message="登录成功",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int((access_expires - datetime.utcnow()).total_seconds()),
        user=UserResponse.model_validate(user)
    )


@router.post("/logout", response_model=dict)
async def logout(
    db: AsyncSession = Depends(get_db_session)
):
    """
    用户登出

    注意：当前实现为服务端操作，客户端需要清除本地存储的token
    """
    return {
        "code": 0,
        "message": "登出成功"
    }


@router.get("/profile", response_model=dict)
async def get_profile(
    db: AsyncSession = Depends(get_db_session)
):
    """获取当前用户信息"""
    return {
        "code": 0,
        "message": "success",
        "data": {}
    }


@router.get("/profile/{user_id}", response_model=dict)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取指定用户信息

    参数:
        user_id: 用户ID
    """
    user = await AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return {
        "code": 0,
        "message": "success",
        "data": UserResponse.model_validate(user)
    }


@router.put("/profile/{user_id}", response_model=dict)
async def update_profile(
    user_id: int,
    request: UserUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新用户信息

    请求示例:
    ```json
    {
      "nickname": "新昵称",
      "email": "new@email.com",
      "phone": "13800138000"
    }
    ```
    """
    user = await AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新字段
    if request.nickname is not None:
        user.nickname = request.nickname
    if request.email is not None:
        user.email = request.email
    if request.phone is not None:
        user.phone = request.phone

    await db.commit()
    await db.refresh(user)

    return {
        "code": 0,
        "message": "更新成功",
        "data": UserResponse.model_validate(user)
    }


@router.post("/change-password", response_model=dict)
async def change_password(
    request: ChangePassword,
    db: AsyncSession = Depends(get_db_session)
):
    """
    修改密码

    请求示例:
    ```json
    {
      "old_password": "old123456",
      "new_password": "new123456",
      "new_password_confirm": "new123456"
    }
    ```
    """
    # 获取当前用户ID
    from fastapi import Request
    # 需要从请求中获取用户ID，这里简化处理
    # 实际应用中需要通过认证中间件获取
    user_id = 1  # TODO: 从认证上下文获取

    user = await AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 验证旧密码
    if not AuthService.verify_password(request.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    # 验证新密码确认
    if request.new_password != request.new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的新密码不一致"
        )

    # 更新密码
    user.password_hash = AuthService.get_password_hash(request.new_password)
    await db.commit()

    return {
        "code": 0,
        "message": "密码修改成功"
    }
