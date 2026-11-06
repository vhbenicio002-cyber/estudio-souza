from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Time
from app.database import Base
from datetime import datetime, time


class ConfiguracaoBarbearia(Base):
    __tablename__ = "configuracao_barbearia"

    id = Column(Integer, primary_key=True, index=True)
    # Horário de funcionamento
    abre_segunda = Column(Boolean, default=True)
    fecha_segunda = Column(Time, default=time(18, 0))
    abre_terca = Column(Boolean, default=True)
    fecha_terca = Column(Time, default=time(18, 0))
    abre_quarta = Column(Boolean, default=True)
    fecha_quarta = Column(Time, default=time(18, 0))
    abre_quinta = Column(Boolean, default=True)
    fecha_quinta = Column(Time, default=time(18, 0))
    abre_sexta = Column(Boolean, default=True)
    fecha_sexta = Column(Time, default=time(18, 0))
    abre_sabado = Column(Boolean, default=True)
    fecha_sabado = Column(Time, default=time(16, 0))
    abre_domingo = Column(Boolean, default=False)
    fecha_domingo = Column(Time, default=time(12, 0))

    # Configurações gerais
    nome_barbearia = Column(String(100), default="Estúdio Souza")
    telefone_contato = Column(String(20))
    email_contato = Column(String(100))
    endereco = Column(Text)
    instagram = Column(String(100))
    whatsapp_numero = Column(String(20))

    # Agendamento
    intervalo_slots_minutos = Column(Integer, default=30)
    antecedencia_minima_horas = Column(Integer, default=1)
    antecedencia_maxima_dias = Column(Integer, default=30)
    permite_cancelamento_horas = Column(Integer, default=2)

    # Fidelidade
    pontos_por_real = Column(Integer, default=1)
    pontos_corte_gratis = Column(Integer, default=100)
    nivel_prata_pontos = Column(Integer, default=200)
    nivel_ouro_pontos = Column(Integer, default=500)
    nivel_diamante_pontos = Column(Integer, default=1000)

    # WhatsApp
    whatsapp_lembrete_horas = Column(Integer, default=2)
    whatsapp_confirmacao_ativa = Column(Boolean, default=True)
    whatsapp_lembrete_ativo = Column(Boolean, default=True)

    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)