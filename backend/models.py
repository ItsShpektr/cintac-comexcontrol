from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base  # Asegúrate de importar Base desde donde lo tengas definido (ej: database.py)

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())