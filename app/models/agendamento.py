from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class StatusAgendamento(str, enum.Enum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"
    NAO_COMPARECEU = "nao_compareceu"


class Agendamento(Base):
    __tablename__ = "agendamentos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=False)
    barbeiro_id = Column(Integer, ForeignKey("barbeiros.id"), nullable=True, index=True)
    data_hora = Column(DateTime, nullable=False, index=True)
    duracao_minutos = Column(Integer, nullable=False)  # copiado do serviço no momento
    preco = Column(Numeric(10, 2), nullable=False)  # copiado do serviço no momento
    status = Column(SQLEnum(StatusAgendamento), default=StatusAgendamento.PENDENTE, index=True)
    observacoes = Column(Text, nullable=True)
    lembrete_enviado = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    concluido_em = Column(DateTime, nullable=True)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="agendamentos")
    servico = relationship("Servico", back_populates="agendamentos")
    barbeiro = relationship("Barbeiro", back_populates="agendamentos")