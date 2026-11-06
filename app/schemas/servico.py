from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class ServicoBase:
    nome: str
    descricao: Optional[str] = None
    preco: Decimal = Decimal('0')
    duracao_minutos: int = 30
    categoria: Optional[str] = None
    ordem: int = 0

    def __post_init__(self):
        if self.preco < 0:
            raise ValueError("Preço não pode ser negativo")
        if self.duracao_minutos <= 0 or self.duracao_minutos > 480:
            raise ValueError("Duração deve ser entre 1 e 480 minutos")


@dataclass
class ServicoCreate(ServicoBase):
    pass


@dataclass
class ServicoUpdate:
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco: Optional[Decimal] = None
    duracao_minutos: Optional[int] = None
    categoria: Optional[str] = None
    ordem: Optional[int] = None
    ativo: Optional[bool] = None


@dataclass
class ServicoResponse:
    id: int
    nome: str
    descricao: Optional[str]
    preco: Decimal
    duracao_minutos: int
    categoria: Optional[str]
    ordem: int
    ativo: bool
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    @classmethod
    def from_orm(cls, servico):
        return cls(
            id=servico.id,
            nome=servico.nome,
            descricao=servico.descricao,
            preco=servico.preco,
            duracao_minutos=servico.duracao_minutos,
            categoria=servico.categoria,
            ordem=servico.ordem,
            ativo=servico.ativo,
            criado_em=servico.criado_em,
            atualizado_em=servico.atualizado_em
        )