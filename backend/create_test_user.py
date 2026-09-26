"""
Quick script to create a test user for testing the v1 API.
Run with: python create_test_user.py
"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.user import User

settings = get_settings()


async def create_test_user():
    """Create a test user if one doesn't exist."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Use a known UUID for testing
        test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        
        # Check if user already exists
        existing = await session.get(User, test_user_id)
        if existing:
            print(f"✓ Test user already exists: {existing.email}")
            print(f"  User ID: {existing.id}")
            return existing.id
        
        # Create new test user
        user = User(
            id=test_user_id,
            name="Test User",
            email="test@example.com",
            career_goal="Full-Stack Developer",
        )
        session.add(user)
        await session.commit()
        
        print(f"✓ Created test user: {user.email}")
        print(f"  User ID: {user.id}")
        print(f"\nYou can now use this user_id in the frontend:")
        print(f"  {user.id}")
        
        return user.id


if __name__ == "__main__":
    asyncio.run(create_test_user())
