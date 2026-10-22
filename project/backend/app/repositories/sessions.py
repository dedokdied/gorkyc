from sqlalchemy.ext.asyncio import AsyncSession


# placeholder for session/message persistence (B zone); keep minimal
class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
