import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.session import AsyncSessionLocal
from app.db.models.data_source import DataSource
from app.db.models.dataset import Dataset
from app.db.models.provenance import DataProvenance
from app.db.models.vessel import Vessel, VesselPosition
from app.services.data.vessel.digitraffic import DigitrafficProvider

async def main():
    async with AsyncSessionLocal() as db:
        provider = DigitrafficProvider()
        desc = provider.descriptor

        # 9. CREATE/REUSE DATA SOURCE RECORD
        src_res = await db.execute(select(DataSource).where(DataSource.name == desc.data_source_name))
        src = src_res.scalars().first()
        if not src:
            src = DataSource(
                name=desc.data_source_name,
                provider="Digitraffic",
                source_type="API",
                description=desc.name,
                base_url=desc.api_url,
                authentication_type="None",
                is_active=True
            )
            db.add(src)
            await db.commit()
            await db.refresh(src)
            print(f"Created data source {src.name} with id {src.id}")
        else:
            print(f"Found data source {src.name} with id {src.id}")

        # 10. CREATE/REUSE DATASET RECORD
        ds_res = await db.execute(select(Dataset).where(Dataset.dataset_name == desc.positions_dataset, Dataset.data_source_id == src.id))
        dataset = ds_res.scalars().first()
        if not dataset:
            dataset = Dataset(
                data_source_id=src.id,
                dataset_name=desc.positions_dataset,
                data_type="VESSEL_LOCATIONS",
                description="AIS vessel positions and metadata from Digitraffic/Fintraffic",
                dataset_identifier="DIGITRAFFIC_AIS",
                is_active=True
            )
            db.add(dataset)
            await db.commit()
            await db.refresh(dataset)
            print(f"Created dataset {dataset.dataset_name} with id {dataset.id}")
        else:
            print(f"Found dataset {dataset.dataset_name} with id {dataset.id}")

        print("Fetching metadata from Digitraffic...")
        since = datetime.now(timezone.utc) - timedelta(hours=24) # just some limit
        metadata_list = await provider.get_vessels_metadata(since)
        print(f"Fetched {len(metadata_list)} metadata records")
        
        # Build dict of metadata
        meta_dict = {m.external_id: m for m in metadata_list}

        print("Fetching locations from Digitraffic...")
        # To avoid unbounded data, we use the Digitraffic API but maybe it only gives the latest.
        # The digitraffic /locations endpoint gives latest position for all active vessels.
        # It's bounded to currently active ships.
        res = await provider.get_vessels(None, since)
        print(f"Fetched {res.records_received} location records. Rejected {res.records_rejected}. Reasons: {res.rejection_reasons}")

        # INSERT / UPSERT Vessels
        vessels_inserted = 0
        vessels_updated = 0
        positions_inserted = 0
        duplicates = 0
        invalid_coords = 0
        
        # Let's map out vessels
        unique_mmsis = set([p.mmsi for p in res.positions])
        
        print(f"Processing {len(unique_mmsis)} unique vessels...")
        
        # Prepare Vessel UPSERT
        vessel_values = []
        now = datetime.now(timezone.utc)
        for p in res.positions:
            m_data = meta_dict.get(p.mmsi)
            vessel_values.append({
                "source_id": src.id,
                "external_vessel_id": p.mmsi,
                "mmsi": p.mmsi,
                "imo": m_data.imo if m_data else None,
                "name": m_data.name if m_data else None,
                "call_sign": m_data.call_sign if m_data else None,
                "vessel_type": None, # or map from ais_ship_type
                "ais_ship_type": m_data.ais_ship_type if m_data else None,
                "length_m": m_data.length_m if m_data else None,
                "width_m": m_data.width_m if m_data else None,
                "draught_m": m_data.draught_m if m_data else None,
                "destination": m_data.destination if m_data else None,
                "metadata_source_timestamp": m_data.source_timestamp if m_data else None,
                "metadata_retrieved_at": now if m_data else None,
                "updated_at": now
            })
            
        # Deduplicate vessel values
        seen_v = set()
        dedup_vessel_values = []
        for v in vessel_values:
            if v["external_vessel_id"] not in seen_v:
                seen_v.add(v["external_vessel_id"])
                dedup_vessel_values.append(v)
                
        if dedup_vessel_values:
            stmt = insert(Vessel).values(dedup_vessel_values)
            stmt = stmt.on_conflict_do_update(
                index_elements=['source_id', 'external_vessel_id'],
                set_={
                    'imo': stmt.excluded.imo,
                    'name': stmt.excluded.name,
                    'call_sign': stmt.excluded.call_sign,
                    'ais_ship_type': stmt.excluded.ais_ship_type,
                    'length_m': stmt.excluded.length_m,
                    'width_m': stmt.excluded.width_m,
                    'draught_m': stmt.excluded.draught_m,
                    'destination': stmt.excluded.destination,
                    'metadata_source_timestamp': stmt.excluded.metadata_source_timestamp,
                    'metadata_retrieved_at': stmt.excluded.metadata_retrieved_at,
                    'updated_at': stmt.excluded.updated_at
                }
            ).returning(Vessel.id, Vessel.external_vessel_id)
            
            res_v = await db.execute(stmt)
            vessel_id_map = {row.external_vessel_id: row.id for row in res_v.fetchall()}
            await db.commit()
            print(f"Upserted {len(dedup_vessel_values)} vessels")
        else:
            vessel_id_map = {}
            
        # Provenance record for this batch
        prov = DataProvenance(
            dataset_id=dataset.id,
            source_id=src.id,
            retrieved_at=now,
            request_parameters={"type": "latest_positions"},
            source_response_code="200",
            records_received=res.records_received,
            records_inserted=len(res.positions)
        )
        db.add(prov)
        await db.commit()
        await db.refresh(prov)
        
        # INSERT / UPSERT VesselPositions
        pos_values = []
        for p in res.positions:
            v_id = vessel_id_map.get(p.mmsi)
            if not v_id:
                continue
                
            if not (-90 <= p.latitude <= 90) or not (-180 <= p.longitude <= 180):
                invalid_coords += 1
                continue
                
            pos_values.append({
                "vessel_id": v_id,
                "source_id": src.id,
                "dataset_id": dataset.id,
                "provenance_id": prov.id,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "geom": f"SRID=4326;POINT({p.longitude} {p.latitude})",
                "timestamp": p.timestamp,
                "retrieved_at": p.retrieved_at,
                "speed_knots": p.speed_knots,
                "course_degrees": p.course_degrees,
                "heading_degrees": p.heading_degrees,
                "navigation_status": p.navigation_status,
                "metadata_": p.metadata,
                "created_at": now
            })
            
        if pos_values:
            stmt = insert(VesselPosition).values(pos_values)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=['source_id', 'vessel_id', 'timestamp']
            )
            res_pos = await db.execute(stmt)
            await db.commit()
            print(f"Inserted {res_pos.rowcount} positions. Duplicates skipped: {len(pos_values) - res_pos.rowcount}")

        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
