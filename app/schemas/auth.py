from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Token:
    access_token: str
    expires_in: int
    token_type: str = "bearer"


@dataclass
class TokenData:
    email: Optional[str] = None
    user_id: Optional[int] = None
    tipo: Optional[str] = None


@dataclass
class LoginRequest:
    email: str
    password: str


@dataclass
class LoginResponse:
    access_token: str
    token_type: str
    expires_in: int
    user: dict