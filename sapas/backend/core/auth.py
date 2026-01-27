"""
认证与授权服务
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..config import get_settings
from ..models import User
from ..schemas.user import UserLogin, UserRegister, TokenResponse, UserResponse

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """认证服务"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
        """
        创建访问令牌

        返回: (token, expires_at)
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
            to_encode.update({"exp": expire.timestamp()})
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
            to_encode.update({"exp": expire.timestamp()})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt, expire

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        to_encode.update({"exp": (datetime.utcnow() + timedelta(days=7)).timestamp()})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> dict:
        """解码令牌"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return {}

    @staticmethod
    async def get_user_by_username(
        session: AsyncSession,
        username: str
    ) -> Optional[User]:
        """通过用户名获取用户"""
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(
        session: AsyncSession,
        user_id: int
    ) -> Optional[User]:
        """通过ID获取用户"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_current_user_id(authorization: Optional[str] = None) -> Optional[int]:
        """
        从Authorization头获取当前用户ID

        使用示例:
            user_id = get_current_user_id(request.headers.get("Authorization"))
        """
        if not authorization:
            return None

        try:
            token = authorization.replace("Bearer ", "")
            payload = AuthService.decode_token(token)
            user_id = payload.get("sub")
            return int(user_id) if user_id else None
        except Exception:
            return None


# 依赖注入函数（用于FastAPI Depends）
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    """获取当前登录用户"""
    try:
        payload = AuthService.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None

        from ..core.database import get_db_session
        async with get_db_session() as db:
            user = await AuthService.get_user_by_id(db, int(user_id))
            if not user or not user.is_active:
                return None
            return user

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证信息"
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[int]:
    """获取当前用户ID（简化版）"""
    try:
        payload = AuthService.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证信息"
        )
