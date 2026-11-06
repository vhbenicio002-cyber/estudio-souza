from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.models.fidelidade import TipoTransacaoFidelidade


@dataclass
class FidelidadeResponse:
    id: int
    cliente_id: int
    pontos_atual: int
    pontos_total_ganho: int
    pontos_total_resgatado: int
    nivel: str
    atualizado_em: datetime

    @classmethod
    def from_orm(cls, fidelidade):
        return cls(
            id=fidelidade.id,
            cliente_id=fidelidade.cliente_id,
            pontos_atual=fidelidade.pontos_atual,
            pontos_total_ganho=fidelidade.pontos_total_ganho,
            pontos_total_resgatado=fidelidade.pontos_total_resgatado,
            nivel=fidelidade.nivel,
            atualizado_em=fidelidade.atualizado_em
        )


@dataclass
class TransacaoFidelidadeResponse:
    id: int
    fidelidade_id: int
    tipo: TipoTransacaoFidelidade
    pontos: int
    descricao: Optional[str]
    agendamento_id: Optional[int]
    criado_em: datetime

    @classmethod
    def from_orm(cls, transacao):
        return cls(
            id=transacao.id,
            fidelidade_id=transacao.fidelidade_id,
            tipo=transacao.tipo,
            pontos=transacao.pontos,
            descricao=transacao.descricao,
            agendamento_id=transacao.agendamento_id,
            criado_em=transacao.criado_em
        )


@dataclass
class ResgateRequest:
    pontos: int
    descricao: Optional[str] = None