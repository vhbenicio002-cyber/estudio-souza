# Schemas module - using plain Python classes for validation
# Import all schemas for convenience
from app.schemas.user import *
from app.schemas.cliente import *
from app.schemas.servico import *
from app.schemas.agendamento import *
from app.schemas.fidelidade import *
from app.schemas.configuracao import *
from app.schemas.auth import *
from app.schemas.whatsapp import *

__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "BarbeiroBase", "BarbeiroCreate", "BarbeiroUpdate", "BarbeiroResponse",
    "ClienteBase", "ClienteCreate", "ClienteUpdate", "ClienteResponse",
    "ClienteComFidelidade",
    "ServicoBase", "ServicoCreate", "ServicoUpdate", "ServicoResponse",
    "AgendamentoBase", "AgendamentoCreate", "AgendamentoUpdate", "AgendamentoResponse",
    "AgendamentoCompleto", "SlotDisponivel",
    "FidelidadeResponse", "TransacaoFidelidadeResponse", "ResgateRequest",
    "ConfiguracaoBase", "ConfiguracaoUpdate", "ConfiguracaoResponse",
    "Token", "TokenData", "LoginRequest",
    "WhatsAppMessage", "WhatsAppWebhook",
]