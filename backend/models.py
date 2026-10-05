from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False, default="Analista COMEX")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cotizaciones = relationship("Cotizacion", back_populates="usuario")
    auditorias = relationship("Auditoria", back_populates="usuario")


class VersionTarifa(Base):
    __tablename__ = "versiones_tarifa"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(255), nullable=False)
    hash_archivo = Column(String(64), nullable=False, index=True)
    estado = Column(String(30), nullable=False, default="PENDIENTE", index=True)
    total_filas = Column(Integer, nullable=False, default=0)
    filas_validas = Column(Integer, nullable=False, default=0)
    filas_invalidas = Column(Integer, nullable=False, default=0)
    resumen_validacion = Column(JSON, nullable=False, default=dict)
    creada_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    tarifas = relationship("Tarifa", back_populates="version", cascade="all, delete-orphan")


class Tarifa(Base):
    __tablename__ = "tarifas"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("versiones_tarifa.id", ondelete="CASCADE"), nullable=False, index=True)
    puerto_origen = Column(String(120), nullable=False, index=True)
    pais_origen = Column(String(120), nullable=True)
    puerto_destino = Column(String(120), nullable=False, index=True)
    tipo_ruta = Column(String(120), nullable=False)
    tarifa_20_min = Column(Float, nullable=False)
    tarifa_20_max = Column(Float, nullable=False)
    tarifa_40_min = Column(Float, nullable=False)
    tarifa_40_max = Column(Float, nullable=False)
    transito_min = Column(Integer, nullable=False)
    transito_max = Column(Integer, nullable=False)
    fuente = Column(String(255), nullable=True)

    version = relationship("VersionTarifa", back_populates="tarifas")


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("versiones_tarifa.id"), nullable=False, index=True)
    puerto_origen = Column(String(120), nullable=False)
    puerto_destino = Column(String(120), nullable=False)
    tipo_contenedor = Column(String(10), nullable=False)
    peso_toneladas = Column(Float, nullable=False)
    cantidad_contenedores = Column(Integer, nullable=False)
    contingencia_dias = Column(Integer, nullable=False, default=0)
    tipo_cambio_clp_usd = Column(Float, nullable=True)
    resultado_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    usuario = relationship("Usuario", back_populates="cotizaciones")


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    accion = Column(String(80), nullable=False, index=True)
    recurso = Column(String(80), nullable=False)
    recurso_id = Column(String(80), nullable=True)
    detalle = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    usuario = relationship("Usuario", back_populates="auditorias")
