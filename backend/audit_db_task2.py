import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
engine = create_async_engine(os.getenv("DATABASE_URL"))
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def audit():
    async with AsyncSessionLocal() as session:
        # Tables to check
        tables = [
            "infrastructure_data", "population_data", "marine_observations",
            "cyclone_events", "cyclone_track_points", "vessels", "vessel_positions",
            "data_sources", "datasets", "data_provenance"
        ]
        print("--- Table Row Counts ---")
        for table in tables:
            try:
                res = await session.execute(text(f"SELECT count(*) FROM {table}"))
                print(f"{table}: {res.scalar()}")
            except Exception as e:
                print(f"{table}: Error - {e}")
        
        print("\n--- Geometry Columns ---")
        res = await session.execute(text("""
            SELECT f_table_name, f_geometry_column, srid, type 
            FROM geometry_columns
        """))
        for row in res.fetchall():
            print(f"Table: {row[0]}, Column: {row[1]}, SRID: {row[2]}, Type: {row[3]}")
            
        print("\n--- Spatial Indexes ---")
        res = await session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes 
            WHERE indexdef LIKE '%gist%'
        """))
        for row in res.fetchall():
            print(f"Index: {row[0]}")
            
        print("\n--- Data Sources ---")
        res = await session.execute(text("SELECT id, name, provider FROM data_sources"))
        for row in res.fetchall():
            print(f"ID: {row[0]}, Name: {row[1]}, Provider: {row[2]}")
            
        print("\n--- Datasets ---")
        res = await session.execute(text("SELECT id, dataset_name, data_source_id FROM datasets"))
        for row in res.fetchall():
            print(f"ID: {row[0]}, Name: {row[1]}, Source ID: {row[2]}")

if __name__ == "__main__":
    asyncio.run(audit())
