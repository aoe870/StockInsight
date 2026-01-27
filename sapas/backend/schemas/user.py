"""
用户相关数据模型
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime
from .common import ApiResponse


class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    password_confirm: str = Field(..., min_length=6, max_length=50, description="确认密码")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., min_length=1, description="密码")
    remember_me: bool = Field(default=False, description="记住登录状态")


class UserUpdate(BaseModel):
    """用户更新请求"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: Optional[str]
    nickname: Optional[str]
    role: str
    avatar: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(ApiResponse):
    """Token 响应"""
    access_token: str = Field(description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    expires_in: int = Field(description="过期时间（秒）")
    user: UserResponse = Field(description="用户信息")


class ChangePassword(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=1, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")
    new_password_confirm: str = Field(..., min_length=6, max_length=50, description="确认新密码")
