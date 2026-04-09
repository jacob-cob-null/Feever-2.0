from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, MedicalService
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.create_tables()

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def insert_service(self, data: Dict) -> MedicalService:
        with self.SessionLocal() as session:
            service = MedicalService(**data)
            session.add(service)
            session.commit()
            session.refresh(service)
            return service

    def insert_batch(self, services_data: List[Dict]) -> List[MedicalService]:
        services = []
        with self.SessionLocal() as session:
            for data in services_data:
                service = MedicalService(**data)
                session.add(service)
                services.append(service)
            session.commit()
            for service in services:
                session.refresh(service)
        return services

    def query_by_facility(self, facility: str) -> List[MedicalService]:
        with self.SessionLocal() as session:
            return session.query(MedicalService).filter(MedicalService.facility == facility).all()

    def get_statistics(self) -> Dict:
        with self.SessionLocal() as session:
            count = session.query(MedicalService).count()
            return {"total_records": count}
