import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def verify():
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async with engine.connect() as conn:
        version = await conn.scalar(text("SELECT version();"))
        print("VERSION:", version)
        
        server_version = await conn.scalar(text("SHOW server_version;"))
        print("SERVER_VERSION:", server_version)
        
        data_directory = await conn.scalar(text("SHOW data_directory;"))
        print("DATA_DIRECTORY:", data_directory)
        
        config_file = await conn.scalar(text("SHOW config_file;"))
        print("CONFIG_FILE:", config_file)
        
        current_db = await conn.scalar(text("SELECT current_database();"))
        print("CURRENT_DATABASE:", current_db)
        
        current_user = await conn.scalar(text("SELECT current_user;"))
        print("CURRENT_USER:", current_user)
        
        extensions = await conn.execute(text("SELECT * FROM pg_available_extensions WHERE name LIKE 'postgis%';"))
        print("AVAILABLE_POSTGIS_EXTENSIONS:")
        for row in extensions:
            print(f"- {row.name} (default_version: {row.default_version})")

asyncio.run(verify())
