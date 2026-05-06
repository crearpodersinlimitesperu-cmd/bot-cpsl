import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuración de la base de datos
# En Render, se puede usar DATABASE_URL. Si no existe, usamos SQLite local.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./bot_cpsl.db")

# Ajuste para DATABASE_URL de Render/Heroku (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    pool_size=10 if "sqlite" not in DATABASE_URL else None, 
    max_overflow=20 if "sqlite" not in DATABASE_URL else None, 
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Modelos ---

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    telefono = Column(String, unique=True, index=True)
    tipo = Column(String)  # e.g. "PX", "IMO", "NUEVO", "CC"
    cc_coordinadora = Column(String)  # Key o teléfono de la coordinadora
    staff_nom = Column(String)
    graduado = Column(Boolean, default=False)
    state_json = Column(Text, nullable=True) # Almacena el estado de la sesión en JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Campana(Base):
    __tablename__ = "campanas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True) # e.g. "C1 E28"
    fecha_inicio = Column(DateTime)
    fecha_fin = Column(DateTime)
    activo = Column(Boolean, default=False)

class Caso(Base):
    __tablename__ = "casos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    campana_id = Column(Integer, ForeignKey("campanas.id"))
    estado = Column(String)  # e.g. "pendiente", "cerrado", "urgente"
    asunto = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

class Derivacion(Base):
    __tablename__ = "derivaciones"
    id = Column(Integer, primary_key=True, index=True)
    caso_id = Column(Integer, ForeignKey("casos.id"))
    coordinadora_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha_asignacion = Column(DateTime, default=datetime.utcnow)
    fecha_cierre = Column(DateTime, nullable=True)

class LogEnvio(Base):
    """La 'Caja Negra' del sistema."""
    __tablename__ = "logs_envio"
    id = Column(Integer, primary_key=True, index=True)
    telefono = Column(String, index=True)
    tipo = Column(String)  # "IN" (Entrante) o "OUT" (Saliente)
    mensaje = Column(Text)
    status_code = Column(Integer) # Respuesta de Meta (e.g. 200)
    error = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

# --- Utilidades ---

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
