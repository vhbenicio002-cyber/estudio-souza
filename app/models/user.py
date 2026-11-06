from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class TipoUsuario(str, enum.Enum):
    ADMIN = "admin"
    BARBEIRO = "barbeiro"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    tipo = Column(SQLEnum(TipoUsuario), default=TipoUsuario.ADMIN, nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    barbeiro = relationship("Barbeiro", back_populates="user", uselist=False)


class Barbeiro(Base):
    __tablename__ = "barbeiros"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    telefone = Column(String(20))
    comissao_percentual = Column(Integer, default=50)  # %
    especialidades = Column(String)  # JSON string ou texto livre
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    user = relationship("User", back_populates="barbeiro")
    agendamentos = relationship("Agendamento", back_populates="barbeiro")