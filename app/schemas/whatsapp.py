from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class WhatsAppMessage:
    to: str
    message: str
    message_type: str = "text"
    template_name: Optional[str] = None
    template_params: Optional[Dict[str, Any]] = None


@dataclass
class WhatsAppWebhook:
    event: str
    instance_id: Optional[str] = None
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class WhatsAppStatus:
    message_id: str
    status: str
    timestamp: datetime
    error: Optional[str] = None