"""Simple database connection test"""
import asyncio
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql+asyncpg://sapas:sapas_password@localhost:5432/sapas'

engine = create_engine(DATABASE_URL, echo=False)

async def test_connection():
    print("Testing database connection...")
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            await conn.commit()
        print("Database connection test: OK!")
    return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
