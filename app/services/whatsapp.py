import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.config import settings
from app.schemas.whatsapp import WhatsAppMessage, WhatsAppStatus

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        self.provider = settings.WHATSAPP_PROVIDER
        self.api_url = settings.WHATSAPP_API_URL
        self.api_token = settings.WHATSAPP_API_TOKEN
        self.instance_id = settings.WHATSAPP_INSTANCE_ID
        self.from_number = settings.WHATSAPP_FROM_NUMBER

    async def send_message(self, message: WhatsAppMessage) -> WhatsAppStatus:
        """Envia mensagem via WhatsApp"""
        if self.provider == "mock":
            return await self._send_mock(message)
        elif self.provider == "twilio":
            return await self._send_twilio(message)
        elif self.provider == "zapi":
            return await self._send_zapi(message)
        elif self.provider == "evolution":
            return await self._send_evolution(message)
        else:
            logger.warning(f"Provedor WhatsApp desconhecido: {self.provider}")
            return await self._send_mock(message)

    async def _send_mock(self, message: WhatsAppMessage) -> WhatsAppStatus:
        """Mock para desenvolvimento/teste - apenas loga a mensagem"""
        logger.info(f"[MOCK WHATSAPP] Para: {message.to} | Mensagem: {message.message}")
        return WhatsAppStatus(
            message_id="mock_" + str(hash(message.message)),
            status="sent",
            timestamp=datetime.utcnow(),
        )

    async def _send_twilio(self, message: WhatsAppMessage) -> WhatsAppStatus:
        """Envia via Twilio"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self.instance_id}/Messages.json",
                    auth=(self.instance_id, self.api_token),
                    data={
                        "From": f"whatsapp:{self.from_number}",
                        "To": f"whatsapp:{message.to}",
                        "Body": message.message,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return WhatsAppStatus(
                    message_id=data.get("sid", ""),
                    status="sent",
                    timestamp=datetime.utcnow(),
                )
        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp via Twilio: {e}")
            return WhatsAppStatus(
                message_id="",
                status="failed",
                timestamp=datetime.utcnow(),
                error=str(e),
            )

    async def _send_zapi(self, message: WhatsAppMessage) -> WhatsAppStatus:
        """Envia via Z-API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/instances/{self.instance_id}/token/{self.api_token}/send-text",
                    json={"phone": message.to, "message": message.message},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return WhatsAppStatus(
                    message_id=data.get("messageId", ""),
                    status="sent",
                    timestamp=datetime.utcnow(),
                )
        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp via Z-API: {e}")
            return WhatsAppStatus(
                message_id="",
                status="failed",
                timestamp=datetime.utcnow(),
                error=str(e),
            )

    async def _send_evolution(self, message: WhatsAppMessage) -> WhatsAppStatus:
        """Envia via Evolution API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/message/sendText/{self.instance_id}",
                    headers={"apikey": self.api_token},
                    json={"number": message.to, "text": message.message},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return WhatsAppStatus(
                    message_id=data.get("key", {}).get("id", ""),
                    status="sent",
                    timestamp=datetime.utcnow(),
                )
        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp via Evolution: {e}")
            return WhatsAppStatus(
                message_id="",
                status="failed",
                timestamp=datetime.utcnow(),
                error=str(e),
            )

    def formatar_telefone(self, telefone: str) -> str:
        """Formata telefone para padrão internacional (55DD9XXXXXXXX)"""
        numeros = "".join(filter(str.isdigit, telefone))
        if len(numeros) == 10:
            numeros = "55" + numeros
        elif len(numeros) == 11 and not numeros.startswith("55"):
            numeros = "55" + numeros
        return numeros

    async def enviar_solicitacao_agendamento(
        self,
        cliente_nome: str,
        telefone: str,
        data_hora: str,
        servico: str
    ) -> WhatsAppStatus:
        """Informa ao cliente que a solicitação foi recebida e aguarda confirmação."""
        msg = f"""📩 *Solicitação de Agendamento Recebida!*

Olá {cliente_nome}!

Recebemos seu pedido de agendamento:

📅 Data/Hora: {data_hora}
💅 Serviço: {servico}

Seu horário ainda aguarda confirmação da profissional.
Você receberá uma nova mensagem assim que houver uma resposta.

Estúdio Souza ✨"""

        return await self.send_message(
            WhatsAppMessage(
                to=self.formatar_telefone(telefone),
                message=msg
            )
        )

    async def enviar_confirmacao_agendamento(self, cliente_nome: str, telefone: str, data_hora: str, servico: str) -> WhatsAppStatus:
        msg = f"""✅ *Agendamento Confirmado!*

Olá {cliente_nome}!

Seu agendamento foi confirmado:
📅 Data/Hora: {data_hora}
💅 Serviço: {servico}


Estamos te esperando! Em caso de imprevisto, avise com 2h de antecedência.

Estúdio Souza ✨"""
        return await self.send_message(WhatsAppMessage(to=self.formatar_telefone(telefone), message=msg))

    async def enviar_lembrete_agendamento(self, cliente_nome: str, telefone: str, data_hora: str, servico: str) -> WhatsAppStatus:
        msg = f"""⏰ *Lembrete de Agendamento*

Olá {cliente_nome}!

Lembrando que seu agendamento é daqui a pouco:
📅 {data_hora}
💅 {servico}


Te esperamos! ✨"""
        return await self.send_message(WhatsAppMessage(to=self.formatar_telefone(telefone), message=msg))

    async def enviar_cancelamento_agendamento(self, cliente_nome: str, telefone: str, data_hora: str, servico: str) -> WhatsAppStatus:
        msg = f"""❌ *Agendamento Cancelado*

Olá {cliente_nome}!

Seu agendamento foi cancelado:
📅 {data_hora}
💅 {servico}

Para reagendar, acesse nosso site ou entre em contato.

Estúdio Souza ✨"""
        return await self.send_message(WhatsAppMessage(to=self.formatar_telefone(telefone), message=msg))

    async def enviar_fidelidade_resgatada(self, cliente_nome: str, telefone: str, pontos: int, recompensa: str) -> WhatsAppStatus:
        msg = f"""🎉 *Recompensa Resgatada!*

Parabéns {cliente_nome}!

Você resgatou: {recompensa}
💎 Pontos utilizados: {pontos}

Aproveite seu benefício na próxima visita!

Estúdio Souza ✨"""
        return await self.send_message(WhatsAppMessage(to=self.formatar_telefone(telefone), message=msg))
