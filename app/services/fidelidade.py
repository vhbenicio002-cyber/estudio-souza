from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.fidelidade import Fidelidade, TransacaoFidelidade, TipoTransacaoFidelidade
from app.models.cliente import Cliente
from app.models.configuracao import ConfiguracaoBarbearia
import logging

logger = logging.getLogger(__name__)


class FidelidadeService:
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

    def get_or_create_fidelidade(self, cliente_id: int) -> Fidelidade:
        fidelidade = self.db.query(Fidelidade).filter(Fidelidade.cliente_id == cliente_id).first()
        if not fidelidade:
            fidelidade = Fidelidade(cliente_id=cliente_id, pontos_atual=0)
            self.db.add(fidelidade)
            self.db.commit()
            self.db.refresh(fidelidade)
        return fidelidade

    def calcular_nivel(self, pontos_total: int) -> str:
        config = self.get_config()
        if pontos_total >= config.nivel_diamante_pontos:
            return "diamante"
        elif pontos_total >= config.nivel_ouro_pontos:
            return "ouro"
        elif pontos_total >= config.nivel_prata_pontos:
            return "prata"
        return "bronze"

    def adicionar_pontos(self, cliente_id: int, pontos: int, descricao: str, agendamento_id: Optional[int] = None) -> Fidelidade:
        if not isinstance(pontos, int) or pontos <= 0:
            raise ValueError("A quantidade de pontos deve ser maior que zero")
        # Garante que a configuração exista antes do lock; get_config pode
        # precisar commitar a criação inicial da configuração.
        config = self.get_config()
        self.get_or_create_fidelidade(cliente_id)
        # populate_existing atualiza o saldo após eventual espera pelo lock.
        fidelidade = self.db.query(Fidelidade).filter(
            Fidelidade.cliente_id == cliente_id
        ).with_for_update().populate_existing().first()
        if not fidelidade:
            raise ValueError("Cadastro de fidelidade não encontrado")
        fidelidade.pontos_atual += pontos
        fidelidade.pontos_total_ganho += pontos
        if fidelidade.pontos_total_ganho >= config.nivel_diamante_pontos:
            fidelidade.nivel = "diamante"
        elif fidelidade.pontos_total_ganho >= config.nivel_ouro_pontos:
            fidelidade.nivel = "ouro"
        elif fidelidade.pontos_total_ganho >= config.nivel_prata_pontos:
            fidelidade.nivel = "prata"
        else:
            fidelidade.nivel = "bronze"

        transacao = TransacaoFidelidade(
            fidelidade_id=fidelidade.id,
            tipo=TipoTransacaoFidelidade.GANHO,
            pontos=pontos,
            descricao=descricao,
            agendamento_id=agendamento_id,
        )
        self.db.add(transacao)
        self.db.commit()
        self.db.refresh(fidelidade)
        return fidelidade

    def resgatar_pontos(self, cliente_id: int, pontos: int, descricao: str) -> Fidelidade:
        if not isinstance(pontos, int) or pontos <= 0:
            raise ValueError("A quantidade de pontos deve ser maior que zero")
        # Revalida o saldo após obter lock da linha (PostgreSQL).
        self.get_or_create_fidelidade(cliente_id)
        fidelidade = self.db.query(Fidelidade).filter(
            Fidelidade.cliente_id == cliente_id
        ).with_for_update().populate_existing().first()
        if not fidelidade:
            raise ValueError("Cadastro de fidelidade não encontrado")
        if fidelidade.pontos_atual < pontos:
            raise ValueError("Pontos insuficientes")

        fidelidade.pontos_atual -= pontos
        fidelidade.pontos_total_resgatado += pontos

        transacao = TransacaoFidelidade(
            fidelidade_id=fidelidade.id,
            tipo=TipoTransacaoFidelidade.RESGATE,
            pontos=-pontos,
            descricao=descricao,
        )
        self.db.add(transacao)
        self.db.commit()
        self.db.refresh(fidelidade)
        return fidelidade

    def pode_resgatar_corte_gratis(self, cliente_id: int) -> bool:
        fidelidade = self.get_or_create_fidelidade(cliente_id)
        config = self.get_config()
        return fidelidade.pontos_atual >= config.pontos_corte_gratis

    def get_extrato(self, cliente_id: int, limite: int = 50) -> list:
        fidelidade = self.get_or_create_fidelidade(cliente_id)
        return self.db.query(TransacaoFidelidade).filter(
            TransacaoFidelidade.fidelidade_id == fidelidade.id
        ).order_by(TransacaoFidelidade.criado_em.desc()).limit(limite).all()

    def processar_conclusao_agendamento(self, agendamento_id: int, valor: Optional[float] = None) -> Optional[Fidelidade]:
        """Credita pontos uma única vez, somente após o atendimento ser concluído."""
        from app.models.agendamento import Agendamento, StatusAgendamento

        # Carrega a configuração antes do lock; não há commit durante a seção crítica.
        config = self.get_config()
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).with_for_update().first()
        if not ag or ag.status != StatusAgendamento.CONCLUIDO:
            return None

        ja_processado = self.db.query(TransacaoFidelidade.id).filter(
            TransacaoFidelidade.agendamento_id == agendamento_id,
            TransacaoFidelidade.tipo == TipoTransacaoFidelidade.GANHO,
        ).first()
        if ja_processado:
            return self.db.query(Fidelidade).filter(Fidelidade.cliente_id == ag.cliente_id).first()

        # Usa o preço congelado no agendamento, não o preço atual do catálogo nem
        # um valor enviado pelo navegador/cliente.
        pontos = int(ag.preco * config.pontos_por_real)
        if pontos <= 0:
            return self.db.query(Fidelidade).filter(Fidelidade.cliente_id == ag.cliente_id).first()

        fidelidade = self.db.query(Fidelidade).filter(
            Fidelidade.cliente_id == ag.cliente_id
        ).with_for_update().first()
        if not fidelidade:
            fidelidade = Fidelidade(cliente_id=ag.cliente_id, pontos_atual=0, pontos_total_ganho=0)
            self.db.add(fidelidade)
            self.db.flush()

        fidelidade.pontos_atual += pontos
        fidelidade.pontos_total_ganho += pontos
        if fidelidade.pontos_total_ganho >= config.nivel_diamante_pontos:
            fidelidade.nivel = "diamante"
        elif fidelidade.pontos_total_ganho >= config.nivel_ouro_pontos:
            fidelidade.nivel = "ouro"
        elif fidelidade.pontos_total_ganho >= config.nivel_prata_pontos:
            fidelidade.nivel = "prata"
        else:
            fidelidade.nivel = "bronze"

        self.db.add(TransacaoFidelidade(
            fidelidade_id=fidelidade.id,
            tipo=TipoTransacaoFidelidade.GANHO,
            pontos=pontos,
            descricao=f"Agendamento: {ag.servico.nome}",
            agendamento_id=agendamento_id,
        ))
        try:
            self.db.commit()
        except IntegrityError:
            # Outra requisição concluiu o mesmo atendimento ao mesmo tempo.
            self.db.rollback()
            existente = self.db.query(TransacaoFidelidade.id).filter(
                TransacaoFidelidade.agendamento_id == agendamento_id,
                TransacaoFidelidade.tipo == TipoTransacaoFidelidade.GANHO,
            ).first()
            if existente:
                return self.db.query(Fidelidade).filter(Fidelidade.cliente_id == ag.cliente_id).first()
            raise
        self.db.refresh(fidelidade)
        return fidelidade
