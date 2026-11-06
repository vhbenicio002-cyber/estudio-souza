from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.agendamento import StatusAgendamento
from app.schemas.cliente import ClienteResponse
from app.schemas.servico import ServicoResponse
from app.schemas.user import BarbeiroResponse


@dataclass
class AgendamentoBase:
    cliente_id: int
    servico_id: int
    barbeiro_id: Optional[int] = None
    data_hora: datetime = None
    observacoes: Optional[str] = None

    def __post_init__(self):
        if self.data_hora and self.data_hora < datetime.now():
            raise ValueError("Não é possível agendar no passado")


@dataclass
class AgendamentoCreate(AgendamentoBase):
    pass


@dataclass
class AgendamentoUpdate:
    servico_id: Optional[int] = None
    barbeiro_id: Optional[int] = None
    data_hora: Optional[datetime] = None
    observacoes: Optional[str] = None
    status: Optional[StatusAgendamento] = None


@dataclass
class AgendamentoResponse:
    id: int
    cliente_id: int
    servico_id: int
    barbeiro_id: Optional[int]
    data_hora: datetime
    duracao_minutos: int
    preco: Decimal
    status: StatusAgendamento
    observacoes: Optional[str]
    lembrete_enviado: bool
    criado_em: datetime
    atualizado_em: datetime
    concluido_em: Optional[datetime]

    @classmethod
    def from_orm(cls, agendamento):
        return cls(
            id=agendamento.id,
            cliente_id=agendamento.cliente_id,
            servico_id=agendamento.servico_id,
            barbeiro_id=agendamento.barbeiro_id,
            data_hora=agendamento.data_hora,
            duracao_minutos=agendamento.duracao_minutos,
            preco=agendamento.preco,
            status=agendamento.status,
            observacoes=agendamento.observacoes,
            lembrete_enviado=agendamento.lembrete_enviado,
            criado_em=agendamento.criado_em,
            atualizado_em=agendamento.atualizado_em,
            concluido_em=agendamento.concluido_em
        )


@dataclass
class AgendamentoCompleto(AgendamentoResponse):
    cliente: ClienteResponse
    servico: ServicoResponse
    barbeiro: Optional[BarbeiroResponse] = None


@dataclass
class SlotDisponivel:
    horario: datetime
    barbeiro_id: Optional[int] = None
    barbeiro_nome: Optional[str] = None
    disponivel: bool = True