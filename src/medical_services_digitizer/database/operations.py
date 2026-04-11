import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, MedicalService
from typing import List, Dict

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

    def export_standardized_sql(self, output_path: str, services: List[Dict]) -> str:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        lines = [
            "DROP TABLE IF EXISTS medical_services;",
            "",
            "CREATE TABLE medical_services (",
            "    service_ID INTEGER PRIMARY KEY,",
            "    service_Name TEXT NOT NULL,",
            "    service_Origin TEXT NOT NULL,",
            "    service_Price DOUBLE PRECISION NOT NULL",
            ");",
            "",
        ]

        for service in services:
            service_id = int(service["service_ID"])
            service_name = str(service["service_Name"]).replace("'", "''")
            service_origin = str(service["service_Origin"]).replace("'", "''")
            service_price = float(service["service_Price"])
            lines.append(
                "INSERT INTO medical_services (service_ID, service_Name, service_Origin, service_Price) "
                f"VALUES ({service_id}, '{service_name}', '{service_origin}', {service_price});"
            )

        with open(output_path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")

        return output_path
