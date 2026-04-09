from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class MedicalService(Base):
    __tablename__ = 'medical_services'

    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False, index=True)
    price = Column(Float, nullable=False, index=True)
    facility = Column(String(255), nullable=False, index=True)
    category = Column(String(100), index=True)
    currency = Column(String(10), default='PHP')
    description = Column(Text)
    source_image = Column(String(500))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
