"""
认证服务模块
处理用户认证、JWT令牌生成和验证
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.user import User
from src.utils.logger import logger


class AuthService:
    """认证服务类"""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.jwt_expire_minutes

    # ==================== 密码处理 ====================

    def hash_password(self, password: str) -> str:
        """对密码进行哈希处理"""
        # bcrypt 限制密码最大72字节
        pwd_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            pwd_bytes = plain_password.encode('utf-8')[:72]
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(pwd_bytes, hashed_bytes)
        except Exception:
            return False
    
    # ==================== JWT 令牌 ====================
    
    def create_access_token(self, user_id: UUID, username: str, role: str = "user") -> str:
        """
        创建访问令牌
        
        Args:
            user_id: 用户ID
            username: 用户名
            role: 用户角色
            
        Returns:
            JWT令牌字符串
        """
        expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)
        payload = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[dict]:
        """
        验证令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            解码后的载荷，验证失败返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.debug(f"JWT验证失败: {e}")
            return None
    
    # ==================== 用户认证 ====================
    
    async def authenticate_user(
        self, 
        session: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """
        验证用户登录
        
        Args:
            session: 数据库会话
            username: 用户名
            password: 密码
            
        Returns:
            验证成功返回用户对象，失败返回None
        """
        # 查询用户
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.debug(f"用户不存在: {username}")
            return None
        
        if not user.is_active:
            logger.debug(f"用户已禁用: {username}")
            return None
        
        if not self.verify_password(password, user.password_hash):
            logger.debug(f"密码错误: {username}")
            return None
        
        return user
    
    async def get_user_by_id(self, session: AsyncSession, user_id: UUID) -> Optional[User]:
        """通过ID获取用户"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, session: AsyncSession, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()


# 全局服务实例
auth_service = AuthService()

