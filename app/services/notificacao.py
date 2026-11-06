from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:  # permite iniciar em ambiente sem o extra opcional instalado
    BackgroundScheduler = None
    IntervalTrigger = None
import logging

from app.models.agendamento import Agendamento, StatusAgendamento
from app.models.cliente import Cliente
from app.services.whatsapp import WhatsAppService
from app.services.fidelidade import FidelidadeService
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class NotificacaoService:
    def __init__(self):
        self.scheduler = BackgroundScheduler() if BackgroundScheduler else None
        self.whatsapp = WhatsAppService()

    def start(self):
        """Inicia o agendador de notificações"""
        if self.scheduler is None:
            logger.warning("APScheduler não instalado; lembretes automáticos desativados")
            return
        if self.scheduler.running:
            return
        # Verificar a cada 15 minutos
        self.scheduler.add_job(
            self.verificar_lembretes,
            IntervalTrigger(minutes=15),
            id="verificar_lembretes",
            replace_existing=True,
        )
        # Processar fidelidade de agendamentos concluídos a cada hora
        self.scheduler.add_job(
            self.processar_fidelidade_concluidos,
            IntervalTrigger(hours=1),
            id="processar_fidelidade",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("Serviço de notificações iniciado")

    def stop(self):
        if self.scheduler is not None and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("Serviço de notificações parado")

    def verificar_lembretes(self):
        """Verifica agendamentos que precisam de lembrete"""
        db = SessionLocal()
        try:
            from app.models.configuracao import ConfiguracaoBarbearia
            config = db.query(ConfiguracaoBarbearia).first()
            if not config or not config.whatsapp_lembrete_ativo:
                return

            agora = datetime.utcnow()
            janela_inicio = agora + timedelta(hours=config.whatsapp_lembrete_horas)
            janela_fim = janela_inicio + timedelta(minutes=30)  # Janela de 30 min

            agendamentos = db.query(Agendamento).filter(
                Agendamento.status.in_([StatusAgendamento.PENDENTE, StatusAgendamento.CONFIRMADO]),
                Agendamento.lembrete_enviado == False,
                Agendamento.data_hora >= janela_inicio,
                Agendamento.data_hora < janela_fim,
            ).all()

            for ag in agendamentos:
                self._enviar_lembrete(ag, db)

        except Exception as e:
            logger.error(f"Erro ao verificar lembretes: {e}")
        finally:
            db.close()

    def _enviar_lembrete(self, agendamento: Agendamento, db: Session):
        """Envia lembrete e só registra como enviado após sucesso real."""
        import asyncio

        async def enviar():
            cliente = agendamento.cliente
            servico = agendamento.servico
            return await self.whatsapp.enviar_lembrete_agendamento(
                cliente_nome=cliente.nome,
                telefone=cliente.telefone,
                data_hora=agendamento.data_hora.strftime("%d/%m/%Y às %H:%M"),
                servico=servico.nome,
            )

        try:
            resultado = asyncio.run(enviar())

            if resultado and resultado.status == "sent":
                agendamento.lembrete_enviado = True
                db.commit()
                logger.info(
                    f"Lembrete enviado para agendamento {agendamento.id}"
                )
            else:
                logger.warning(
                    f"Lembrete não enviado para agendamento {agendamento.id}. "
                    f"Status retornado: {getattr(resultado, 'status', 'sem retorno')}"
                )

        except Exception as e:
            logger.error(
                f"Erro ao enviar lembrete para agendamento {agendamento.id}: {e}"
            )

    def processar_fidelidade_concluidos(self):
        """Processa fidelidade para agendamentos concluídos recentemente"""
        db = SessionLocal()
        try:
            fidelidade_service = FidelidadeService(db)
            # Últimas 2 horas
            limite = datetime.utcnow() - timedelta(hours=2)
            agendamentos = db.query(Agendamento).filter(
                Agendamento.status == StatusAgendamento.CONCLUIDO,
                Agendamento.concluido_em >= limite,
            ).all()

            for ag in agendamentos:
                fidelidade_service.processar_conclusao_agendamento(ag.id, float(ag.preco))

        except Exception as e:
            logger.error(f"Erro ao processar fidelidade: {e}")
        finally:
            db.close()

    async def enviar_confirmacao_agendamento(self, agendamento: Agendamento):
        """Envia confirmação de agendamento"""
        cliente = agendamento.cliente
        servico = agendamento.servico
        await self.whatsapp.enviar_confirmacao_agendamento(
            cliente_nome=cliente.nome,
            telefone=cliente.telefone,
            data_hora=agendamento.data_hora.strftime("%d/%m/%Y às %H:%M"),
            servico=servico.nome,
        )

    async def enviar_cancelamento_agendamento(self, agendamento: Agendamento):
        """Envia notificação de cancelamento"""
        cliente = agendamento.cliente
        servico = agendamento.servico

        await self.whatsapp.enviar_cancelamento_agendamento(
            cliente_nome=cliente.nome,
            telefone=cliente.telefone,
            data_hora=agendamento.data_hora.strftime("%d/%m/%Y às %H:%M"),
            servico=servico.nome,
        )

    async def enviar_fidelidade_resgatada(self, cliente_id: int, pontos: int, recompensa: str):
        """Envia notificação de resgate de fidelidade"""
        db = SessionLocal()
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if cliente:
                await self.whatsapp.enviar_fidelidade_resgatada(
                    cliente_nome=cliente.nome,
                    telefone=cliente.telefone,
                    pontos=pontos,
                    recompensa=recompensa,
                )
        finally:
            db.close()


# Instância global
notificacao_service = NotificacaoService()