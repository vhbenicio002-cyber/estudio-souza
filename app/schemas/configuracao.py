from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional
from decimal import Decimal


@dataclass
class ConfiguracaoBase:
    nome_barbearia: str = "Estúdio Souza"
    telefone_contato: Optional[str] = None
    email_contato: Optional[str] = None
    endereco: Optional[str] = None
    instagram: Optional[str] = None
    whatsapp_numero: Optional[str] = None

    abre_segunda: bool = True
    fecha_segunda: time = time(18, 0)
    abre_terca: bool = True
    fecha_terca: time = time(18, 0)
    abre_quarta: bool = True
    fecha_quarta: time = time(18, 0)
    abre_quinta: bool = True
    fecha_quinta: time = time(18, 0)
    abre_sexta: bool = True
    fecha_sexta: time = time(18, 0)
    abre_sabado: bool = True
    fecha_sabado: time = time(16, 0)
    abre_domingo: bool = False
    fecha_domingo: time = time(12, 0)

    intervalo_slots_minutos: int = 30
    antecedencia_minima_horas: int = 1
    antecedencia_maxima_dias: int = 30
    permite_cancelamento_horas: int = 2

    pontos_por_real: int = 1
    pontos_corte_gratis: int = 100
    nivel_prata_pontos: int = 200
    nivel_ouro_pontos: int = 500
    nivel_diamante_pontos: int = 1000

    whatsapp_lembrete_horas: int = 2
    whatsapp_confirmacao_ativa: bool = True
    whatsapp_lembrete_ativo: bool = True


@dataclass
class ConfiguracaoUpdate:
    nome_barbearia: Optional[str] = None
    telefone_contato: Optional[str] = None
    email_contato: Optional[str] = None
    endereco: Optional[str] = None
    instagram: Optional[str] = None
    whatsapp_numero: Optional[str] = None

    abre_segunda: Optional[bool] = None
    fecha_segunda: Optional[time] = None
    abre_terca: Optional[bool] = None
    fecha_terca: Optional[time] = None
    abre_quarta: Optional[bool] = None
    fecha_quarta: Optional[time] = None
    abre_quinta: Optional[bool] = None
    fecha_quinta: Optional[time] = None
    abre_sexta: Optional[bool] = None
    fecha_sexta: Optional[time] = None
    abre_sabado: Optional[bool] = None
    fecha_sabado: Optional[time] = None
    abre_domingo: Optional[bool] = None
    fecha_domingo: Optional[time] = None

    intervalo_slots_minutos: Optional[int] = None
    antecedencia_minima_horas: Optional[int] = None
    antecedencia_maxima_dias: Optional[int] = None
    permite_cancelamento_horas: Optional[int] = None

    pontos_por_real: Optional[int] = None
    pontos_corte_gratis: Optional[int] = None
    nivel_prata_pontos: Optional[int] = None
    nivel_ouro_pontos: Optional[int] = None
    nivel_diamante_pontos: Optional[int] = None

    whatsapp_lembrete_horas: Optional[int] = None
    whatsapp_confirmacao_ativa: Optional[bool] = None
    whatsapp_lembrete_ativo: Optional[bool] = None


@dataclass
class ConfiguracaoResponse:
    id: int
    nome_barbearia: str
    telefone_contato: Optional[str]
    email_contato: Optional[str]
    endereco: Optional[str]
    instagram: Optional[str]
    whatsapp_numero: Optional[str]

    abre_segunda: bool
    fecha_segunda: time
    abre_terca: bool
    fecha_terca: time
    abre_quarta: bool
    fecha_quarta: time
    abre_quinta: bool
    fecha_quinta: time
    abre_sexta: bool
    fecha_sexta: time
    abre_sabado: bool
    fecha_sabado: time
    abre_domingo: bool
    fecha_domingo: time

    intervalo_slots_minutos: int
    antecedencia_minima_horas: int
    antecedencia_maxima_dias: int
    permite_cancelamento_horas: int

    pontos_por_real: int
    pontos_corte_gratis: int
    nivel_prata_pontos: int
    nivel_ouro_pontos: int
    nivel_diamante_pontos: int

    whatsapp_lembrete_horas: int
    whatsapp_confirmacao_ativa: bool
    whatsapp_lembrete_ativo: bool

    criado_em: Optional[datetime]
    atualizado_em: Optional[datetime]

    @classmethod
    def from_orm(cls, config):
        return cls(
            id=config.id,
            nome_barbearia=config.nome_barbearia,
            telefone_contato=config.telefone_contato,
            email_contato=config.email_contato,
            endereco=config.endereco,
            instagram=config.instagram,
            whatsapp_numero=config.whatsapp_numero,
            abre_segunda=config.abre_segunda,
            fecha_segunda=config.fecha_segunda,
            abre_terca=config.abre_terca,
            fecha_terca=config.fecha_terca,
            abre_quarta=config.abre_quarta,
            fecha_quarta=config.fecha_quarta,
            abre_quinta=config.abre_quinta,
            fecha_quinta=config.fecha_quinta,
            abre_sexta=config.abre_sexta,
            fecha_sexta=config.fecha_sexta,
            abre_sabado=config.abre_sabado,
            fecha_sabado=config.fecha_sabado,
            abre_domingo=config.abre_domingo,
            fecha_domingo=config.fecha_domingo,
            intervalo_slots_minutos=config.intervalo_slots_minutos,
            antecedencia_minima_horas=config.antecedencia_minima_horas,
            antecedencia_maxima_dias=config.antecedencia_maxima_dias,
            permite_cancelamento_horas=config.permite_cancelamento_horas,
            pontos_por_real=config.pontos_por_real,
            pontos_corte_gratis=config.pontos_corte_gratis,
            nivel_prata_pontos=config.nivel_prata_pontos,
            nivel_ouro_pontos=config.nivel_ouro_pontos,
            nivel_diamante_pontos=config.nivel_diamante_pontos,
            whatsapp_lembrete_horas=config.whatsapp_lembrete_horas,
            whatsapp_confirmacao_ativa=config.whatsapp_confirmacao_ativa,
            whatsapp_lembrete_ativo=config.whatsapp_lembrete_ativo,
            criado_em=config.criado_em,
            atualizado_em=config.atualizado_em
        )