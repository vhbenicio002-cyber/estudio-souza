from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, index=True)
    telefone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    data_nascimento = Column(DateTime, nullable=True)
    observacoes = Column(Text, nullable=True)
    como_conheceu = Column(String(50), nullable=True)  # indicação, instagram, google, etc
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    agendamentos = relationship("Agendamento", back_populates="cliente", cascade="all, delete-orphan")
    fidelidade = relationship("Fidelidade", back_populates="cliente", uselist=False, cascade="all, delete-orphan")