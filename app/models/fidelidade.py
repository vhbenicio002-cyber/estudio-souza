from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class TipoTransacaoFidelidade(str, enum.Enum):
    GANHO = "ganho"
    RESGATE = "resgate"
    EXPIRACAO = "expiracao"
    AJUSTE = "ajuste"


class Fidelidade(Base):
    __tablename__ = "fidelidades"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), unique=True, nullable=False, index=True)
    pontos_atual = Column(Integer, default=0)
    pontos_total_ganho = Column(Integer, default=0)
    pontos_total_resgatado = Column(Integer, default=0)
    nivel = Column(String(20), default="bronze")  # bronze, prata, ouro, diamante
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="fidelidade")
    transacoes = relationship("TransacaoFidelidade", back_populates="fidelidade", cascade="all, delete-orphan")


class TransacaoFidelidade(Base):
    __tablename__ = "transacoes_fidelidade"

    id = Column(Integer, primary_key=True, index=True)
    fidelidade_id = Column(Integer, ForeignKey("fidelidades.id"), nullable=False, index=True)
    tipo = Column(SQLEnum(TipoTransacaoFidelidade), nullable=False)
    pontos = Column(Integer, nullable=False)  # positivo para ganho, negativo para resgate
    descricao = Column(String(200), nullable=True)
    agendamento_id = Column(Integer, ForeignKey("agendamentos.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    fidelidade = relationship("Fidelidade", back_populates="transacoes")