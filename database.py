import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

# Configuración de la base de datos
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caja_negra.db")

# Ajuste para DATABASE_URL de Render/Heroku (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configuración del Motor con compatibilidad total
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine(
        DATABASE_URL, 
        pool_size=10, 
        max_overflow=20, 
        pool_pre_ping=True
    )

# --- ACTIVACION MODO WAL PARA SQLITE (Evita bloqueos) ---
if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Modelos Enterprise ---

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    telefono = Column(String, unique=True, index=True)
    email = Column(String, index=True)
    documento = Column(String, unique=True, index=True)
    tipo = Column(String)  # e.g. "PX", "IMO", "CC"
    cc_asignada = Column(String)  # Nombre de la CC (Diana/Joyce)
    graduado = Column(Boolean, default=False)
    
    # --- Experience Cloud & Consent ---
    px_score = Column(Integer, default=0)
    journey_stage = Column(String, default="NEW")
    behavioral_tags = Column(Text, nullable=True)
    last_interaction = Column(DateTime, nullable=True)
    
    # Consent Tracking
    tc_version = Column(String, nullable=True) # e.g. "V1.0-2026-05"
    tc_accepted_at = Column(DateTime, nullable=True)
    
    # --- Hygiene & Reputation ---
    email_status = Column(String, default="VALID") # VALID, INVALID, AT_RISK, BOUNCED
    last_bounce_reason = Column(String, nullable=True)
    bounce_count = Column(Integer, default=0)
    
    # Session State (WA session persistence)
    state_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrazabilidadPX(Base):
    """Memoria Eterna de interacciones PX."""
    __tablename__ = "trazabilidad_px"
    id = Column(Integer, primary_key=True, index=True)
    px_id = Column(Integer, ForeignKey("usuarios.id"))
    canal = Column(String)  # "SMS", "EMAIL", "WA"
    tipo_evento = Column(String)  # "ENVIO", "RESPUESTA", "BOUNCE", "RECHAZO"
    contenido = Column(Text)
    detalles = Column(Text, nullable=True) # JSON payload
    timestamp = Column(DateTime, default=datetime.utcnow)

class DecisionIA(Base):
    """Auditoria operativa de decisiones tomadas por agentes IA."""
    __tablename__ = "decisiones_ia"
    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer) # ID del PX o Caso
    tipo_entidad = Column(String) # "PX" o "CASO"
    decision = Column(String)
    contexto = Column(Text) # Por qué se tomó
    timestamp = Column(DateTime, default=datetime.utcnow)

class ReputacionCanal(Base):
    """Monitoreo de salud para evitar bloqueos."""
    __tablename__ = "reputacion_canales"
    id = Column(Integer, primary_key=True, index=True)
    canal = Column(String, unique=True) # "GMAIL", "SMS_GATEWAY"
    envios_hora = Column(Integer, default=0)
    envios_dia = Column(Integer, default=0)
    bounces_recientes = Column(Integer, default=0)
    ultimo_reseteo = Column(DateTime, default=datetime.utcnow)

class LogEnvio(Base):
    """Log crudo de comunicaciones."""
    __tablename__ = "logs_envio"
    id = Column(Integer, primary_key=True, index=True)
    destino = Column(String, index=True)
    tipo = Column(String)  # "IN" o "OUT"
    canal = Column(String) # "SMS", "EMAIL"
    mensaje = Column(Text)
    status_code = Column(Integer)
    error = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

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

# --- CREAR Logistics Cloud Models ---


class Entrenador(Base):
    """Modelo para gestionar entrenadores y staff logístico."""
    __tablename__ = "entrenadores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    email = Column(String, index=True)
    telefono = Column(String)
    rol = Column(String, default="TRAINER") # TRAINER, STAFF, LOGISTICS
    preferencias_viaje = Column(Text, nullable=True) # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

class VueloLogistica(Base):
    """Modelo para seguimiento de vuelos en tiempo real."""
    __tablename__ = "vuelos_logistica"
    id = Column(Integer, primary_key=True, index=True)
    entrenador_id = Column(Integer, ForeignKey("entrenadores.id"))
    codigo_vuelo = Column(String, index=True) # e.g. LA2014
    aerolinea = Column(String)
    origen = Column(String)
    destino = Column(String)
    fecha_hora_salida_prog = Column(DateTime)
    fecha_hora_llegada_prog = Column(DateTime)
    fecha_hora_salida_real = Column(DateTime, nullable=True)
    fecha_hora_llegada_real = Column(DateTime, nullable=True)
    estado = Column(String, default="PROGRAMADO") # PROGRAMADO, RETRASADO, CANCELADO, EN_VUELO, ATERRIZADO
    terminal_puerta = Column(String, nullable=True)
    notas_logistica = Column(Text, nullable=True)
    ultima_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- Utilidades ---

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
