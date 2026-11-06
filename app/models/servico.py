from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Servico(Base):
    __tablename__ = "servicos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    preco = Column(Numeric(10, 2), nullable=False)
    duracao_minutos = Column(Integer, nullable=False, default=30)
    categoria = Column(String(50), nullable=True)  # corte, barba, sobrancelha, combo, etc
    ativo = Column(Boolean, default=True)
    ordem = Column(Integer, default=0)  # para ordenação no cardápio
    pontos_resgate = Column(Integer, nullable=False, default=0)  # custo em pontos para resgatar o serviço
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    agendamentos = relationship("Agendamento", back_populates="servico")