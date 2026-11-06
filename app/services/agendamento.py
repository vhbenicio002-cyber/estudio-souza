from datetime import datetime, time, timedelta, date
from zoneinfo import ZoneInfo
from app.config import settings
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.agendamento import Agendamento, StatusAgendamento
from app.models.servico import Servico
from app.models.configuracao import ConfiguracaoBarbearia
from app.schemas.agendamento import SlotDisponivel
import logging

logger = logging.getLogger(__name__)


def agora_local() -> datetime:
    """Horário local do estúdio, armazenado no banco como datetime sem fuso."""
    return datetime.now(ZoneInfo(settings.TIMEZONE)).replace(tzinfo=None)


def dentro_janela_conclusao(data_hora: datetime, duracao_minutos: int, agora: Optional[datetime] = None) -> bool:
    """Permite concluir do início marcado até 15 min após a duração prevista."""
    momento = agora or agora_local()
    fim_janela = data_hora + timedelta(minutes=duracao_minutos + 15)
    return data_hora <= momento <= fim_janela


class AgendamentoService:
    def __init__(self, db: Session):
        self.db = db

    def get_config(self) -> ConfiguracaoBarbearia:
        config = self.db.query(ConfiguracaoBarbearia).first()
        if not config:
            config = ConfiguracaoBarbearia()
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def get_horario_funcionamento(self, dia_semana: int) -> tuple[bool, Optional[time], Optional[time]]:
        """Retorna (abre, hora_abre, hora_fecha) para o dia da semana (0=segunda)"""
        # Horários definidos para o Estúdio Souza (0=segunda, 6=domingo).
        # Segunda e quarta a domingo: 09h às 20h; terça e quinta: 14h às 20h.
        horarios = [
            (True, time(9, 0), time(20, 0)),   # Segunda
            (True, time(14, 0), time(20, 0)),  # Terça
            (True, time(9, 0), time(20, 0)),   # Quarta
            (True, time(14, 0), time(20, 0)),  # Quinta
            (True, time(9, 0), time(20, 0)),   # Sexta
            (True, time(9, 0), time(20, 0)),   # Sábado
            (True, time(9, 0), time(20, 0)),   # Domingo
        ]
        return horarios[dia_semana]

    def get_slots_disponiveis(self, data: date, barbeiro_id: Optional[int] = None, servico_id: Optional[int] = None) -> List[SlotDisponivel]:
        """Retorna horários livres na agenda única da profissional."""
        config = self.get_config()
        abre, hora_abre, hora_fecha = self.get_horario_funcionamento(data.weekday())
        if not abre or not hora_abre or not hora_fecha:
            return []

        duracao = 30
        if servico_id:
            servico = self.db.query(Servico).filter(Servico.id == servico_id, Servico.ativo == True).first()
            if not servico:
                return []
            duracao = servico.duracao_minutos

        intervalo = max(5, config.intervalo_slots_minutos or 30)
        inicio_dia = datetime.combine(data, time.min)
        fim_dia = inicio_dia + timedelta(days=1)
        agendamentos = self.db.query(Agendamento).filter(
            Agendamento.data_hora >= inicio_dia,
            Agendamento.data_hora < fim_dia,
            Agendamento.status.in_([StatusAgendamento.PENDENTE, StatusAgendamento.CONFIRMADO, StatusAgendamento.EM_ANDAMENTO]),
        ).all()

        atual = datetime.combine(data, hora_abre)
        fim = datetime.combine(data, hora_fecha)
        limite_minimo = agora_local()
        slots = []
        while atual + timedelta(minutes=duracao) <= fim:
            fim_slot = atual + timedelta(minutes=duracao)
            disponivel = atual >= limite_minimo and not any(
                atual < ag.data_hora + timedelta(minutes=ag.duracao_minutos) and fim_slot > ag.data_hora
                for ag in agendamentos
            )
            # Não listar horários que já começaram ou passaram. Para hoje,
            # mostrar somente horários futuros que ainda comportem o serviço.
            if atual >= limite_minimo and disponivel:
                slots.append(SlotDisponivel(horario=atual, disponivel=True))
            atual += timedelta(minutes=intervalo)
        return slots

    def verificar_conflito(self, data_hora: datetime, duracao: int, barbeiro_id: Optional[int] = None, excluir_id: Optional[int] = None) -> bool:
        """Verifica sobreposição na agenda única da profissional."""
        fim = data_hora + timedelta(minutes=duracao)
        query = self.db.query(Agendamento).filter(
            Agendamento.status.in_([StatusAgendamento.PENDENTE, StatusAgendamento.CONFIRMADO, StatusAgendamento.EM_ANDAMENTO]),
            Agendamento.data_hora < fim,
        )
        if excluir_id is not None:
            query = query.filter(Agendamento.id != excluir_id)
        return any(ag.data_hora + timedelta(minutes=ag.duracao_minutos) > data_hora for ag in query.all())

    def criar_agendamento(self, cliente_id: int, servico_id: int, data_hora: datetime, barbeiro_id: Optional[int] = None, observacoes: Optional[str] = None) -> Agendamento:
        """Cria um novo agendamento na agenda única."""
        servico = self.db.query(Servico).filter(Servico.id == servico_id, Servico.ativo == True).first()
        if not servico:
            raise ValueError("Serviço não encontrado ou inativo")
        if data_hora <= agora_local():
            raise ValueError("Não é possível agendar no passado")

        config = self.get_config()
        minimo = agora_local()
        maximo = agora_local() + timedelta(days=config.antecedencia_maxima_dias or 30)
        if data_hora < minimo:
            raise ValueError("Agendamento fora do prazo mínimo de antecedência")
        if data_hora.date() > maximo.date():
            raise ValueError("Agendamento excede o prazo máximo permitido")
        abre, hora_abre, hora_fecha = self.get_horario_funcionamento(data_hora.weekday())
        fim_agendamento = data_hora + timedelta(minutes=servico.duracao_minutos)
        if not abre or not hora_abre or not hora_fecha:
            raise ValueError("O espaço não funciona neste dia")
        if data_hora.time() < hora_abre or fim_agendamento.time() > hora_fecha:
            raise ValueError("Horário fora do funcionamento")
        if self.verificar_conflito(data_hora, servico.duracao_minutos):
            raise ValueError("Este horário não está mais disponível")

        agendamento = Agendamento(
            cliente_id=cliente_id, servico_id=servico_id, barbeiro_id=None,
            data_hora=data_hora, duracao_minutos=servico.duracao_minutos,
            preco=servico.preco, observacoes=observacoes, status=StatusAgendamento.PENDENTE,
        )
        self.db.add(agendamento)
        self.db.commit()
        self.db.refresh(agendamento)
        return agendamento

    def atualizar_status(self, agendamento_id: int, status: StatusAgendamento) -> Optional[Agendamento]:
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        if ag:
            ag.status = status
            if status == StatusAgendamento.CONCLUIDO:
                ag.concluido_em = datetime.utcnow()
            self.db.commit()
            self.db.refresh(ag)
        return ag

    def cancelar_agendamento(self, agendamento_id: int) -> Optional[Agendamento]:
        return self.atualizar_status(agendamento_id, StatusAgendamento.CANCELADO)

    def get_agendamentos_hoje(self) -> List[Agendamento]:
        hoje = agora_local().date()
        return self.db.query(Agendamento).filter(
            Agendamento.data_hora >= datetime.combine(hoje, time(0, 0)),
            Agendamento.data_hora < datetime.combine(hoje + timedelta(days=1), time(0, 0)),
        ).order_by(Agendamento.data_hora).all()

    def get_agendamentos_periodo(self, inicio: datetime, fim: datetime, barbeiro_id: Optional[int] = None) -> List[Agendamento]:
        query = self.db.query(Agendamento).filter(
            Agendamento.data_hora >= inicio,
            Agendamento.data_hora < fim,
        )
        if barbeiro_id:
            query = query.filter(Agendamento.barbeiro_id == barbeiro_id)
        return query.order_by(Agendamento.data_hora).all()