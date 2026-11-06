from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import re


@dataclass
class ClienteBase:
    nome: str
    telefone: str
    email: Optional[str] = None
    data_nascimento: Optional[datetime] = None
    observacoes: Optional[str] = None
    como_conheceu: Optional[str] = None

    def __post_init__(self):
        # Validar telefone
        numeros = re.sub(r'\D', '', self.telefone)
        if len(numeros) < 10 or len(numeros) > 11:
            raise ValueError("Telefone deve ter 10 ou 11 dígitos")


@dataclass
class ClienteCreate(ClienteBase):
    pass


@dataclass
class ClienteUpdate:
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    data_nascimento: Optional[datetime] = None
    observacoes: Optional[str] = None
    como_conheceu: Optional[str] = None
    ativo: Optional[bool] = None


@dataclass
class ClienteResponse:
    id: int
    nome: str
    telefone: str
    email: Optional[str]
    data_nascimento: Optional[datetime]
    observacoes: Optional[str]
    como_conheceu: Optional[str]
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def from_orm(cls, cliente):
        return cls(
            id=cliente.id,
            nome=cliente.nome,
            telefone=cliente.telefone,
            email=cliente.email,
            data_nascimento=cliente.data_nascimento,
            observacoes=cliente.observacoes,
            como_conheceu=cliente.como_conheceu,
            ativo=cliente.ativo,
            criado_em=cliente.criado_em,
            atualizado_em=cliente.atualizado_em
        )


@dataclass
class ClienteComFidelidade(ClienteResponse):
    fidelidade: Optional['FidelidadeResponse'] = None