from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.models.user import TipoUsuario


@dataclass
class UserBase:
    email: str
    nome: str
    tipo: TipoUsuario


@dataclass
class UserCreate(UserBase):
    password: str


@dataclass
class UserUpdate:
    email: Optional[str] = None
    nome: Optional[str] = None
    tipo: Optional[TipoUsuario] = None
    ativo: Optional[bool] = None


@dataclass
class UserResponse:
    id: int
    email: str
    nome: str
    tipo: TipoUsuario
    ativo: bool
    criado_em: datetime

    @classmethod
    def from_orm(cls, user):
        return cls(
            id=user.id,
            email=user.email,
            nome=user.nome,
            tipo=user.tipo,
            ativo=user.ativo,
            criado_em=user.criado_em
        )


@dataclass
class BarbeiroBase:
    telefone: Optional[str]
    comissao_percentual: int
    especialidades: Optional[str]


@dataclass
class BarbeiroCreate(BarbeiroBase):
    user_id: int


@dataclass
class BarbeiroUpdate:
    telefone: Optional[str] = None
    comissao_percentual: Optional[int] = None
    especialidades: Optional[str] = None
    ativo: Optional[bool] = None


@dataclass
class BarbeiroResponse:
    id: int
    user_id: int
    telefone: Optional[str]
    comissao_percentual: int
    especialidades: Optional[str]
    ativo: bool
    criado_em: datetime
    nome: Optional[str] = None
    email: Optional[str] = None

    @classmethod
    def from_orm(cls, barbeiro):
        return cls(
            id=barbeiro.id,
            user_id=barbeiro.user_id,
            telefone=barbeiro.telefone,
            comissao_percentual=barbeiro.comissao_percentual,
            especialidades=barbeiro.especialidades,
            ativo=barbeiro.ativo,
            criado_em=barbeiro.criado_em,
            nome=barbeiro.user.nome if barbeiro.user else None,
            email=barbeiro.user.email if barbeiro.user else None
        )