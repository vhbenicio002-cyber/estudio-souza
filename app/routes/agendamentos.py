from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.database import get_db
from app.models.agendamento import Agendamento, StatusAgendamento
from app.models.cliente import Cliente
from app.models.servico import Servico
from app.services.agendamento import AgendamentoService, agora_local, dentro_janela_conclusao
from app.services.notificacao import notificacao_service
from app.routes.auth import get_current_admin, get_current_user
from app.models.user import User, Barbeiro

router = APIRouter(prefix="/agendamentos", tags=["Agendamentos"])


@router.post("/", status_code=201)
def criar_agendamento(
    cliente_id: int = Body(...),
    servico_id: int = Body(...),
    data_hora: str = Body(...),
    barbeiro_id: Optional[int] = Body(None),
    observacoes: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    try:
        dt = datetime.fromisoformat(data_hora)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data/hora inválido")

    service = AgendamentoService(db)
    try:
        novo = service.criar_agendamento(
            cliente_id=cliente_id,
            servico_id=servico_id,
            data_hora=dt,
            barbeiro_id=barbeiro_id,
            observacoes=observacoes,
        )
        return novo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def listar_agendamentos(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    cliente_id: Optional[int] = None,
    barbeiro_id: Optional[int] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    from sqlalchemy.orm import joinedload
    query = db.query(Agendamento).options(
        joinedload(Agendamento.cliente),
        joinedload(Agendamento.servico),
        joinedload(Agendamento.barbeiro).joinedload(Barbeiro.user)
    )
    if status:
        # Handle comma-separated status values
        status_list = [s.strip() for s in status.split(',')]
        try:
            status_enums = [StatusAgendamento(s) for s in status_list]
            query = query.filter(Agendamento.status.in_(status_enums))
        except ValueError:
            raise HTTPException(status_code=400, detail="Status inválido")
    if cliente_id:
        query = query.filter(Agendamento.cliente_id == cliente_id)
    if barbeiro_id:
        query = query.filter(Agendamento.barbeiro_id == barbeiro_id)
    if data_inicio:
        query = query.filter(Agendamento.data_hora >= datetime.fromisoformat(data_inicio))
    if data_fim:
        query = query.filter(Agendamento.data_hora <= datetime.fromisoformat(data_fim))

    agendamentos = query.order_by(Agendamento.data_hora.desc()).offset(skip).limit(limit).all()

    # Serializar manualmente para incluir relacionamentos
    return [
        {
            "id": a.id,
            "cliente_id": a.cliente_id,
            "cliente": {
                "id": a.cliente.id,
                "nome": a.cliente.nome,
                "telefone": a.cliente.telefone,
                "email": a.cliente.email,
            } if a.cliente else None,
            "servico_id": a.servico_id,
            "servico": {
                "id": a.servico.id,
                "nome": a.servico.nome,
                "preco": float(a.servico.preco),
                "duracao_minutos": a.servico.duracao_minutos,
            } if a.servico else None,
            "barbeiro_id": a.barbeiro_id,
            "barbeiro": {
                "id": a.barbeiro.id,
                "nome": a.barbeiro.user.nome if a.barbeiro.user else "Barbeiro",
            } if a.barbeiro else None,
            "data_hora": a.data_hora.isoformat(),
            "duracao_minutos": a.duracao_minutos,
            "preco": float(a.preco),
            "status": a.status.value,
            "observacoes": a.observacoes,
            "pode_concluir": (
                a.status in [StatusAgendamento.PENDENTE, StatusAgendamento.CONFIRMADO, StatusAgendamento.EM_ANDAMENTO]
                and dentro_janela_conclusao(a.data_hora, a.duracao_minutos)
            ),
            "janela_conclusao_inicio": a.data_hora.isoformat(),
            "janela_conclusao_fim": (a.data_hora + timedelta(minutes=a.duracao_minutos + 15)).isoformat(),
        }
        for a in agendamentos
    ]


@router.get("/hoje")
def agendamentos_hoje(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    service = AgendamentoService(db)
    return service.get_agendamentos_hoje()


@router.get("/slots")
def slots_disponiveis(
    data: str,
    servico_id: Optional[int] = None,
    barbeiro_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        dt = datetime.strptime(data, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido")

    service = AgendamentoService(db)
    return service.get_slots_disponiveis(dt, barbeiro_id, servico_id)


@router.get("/{agendamento_id}")
def obter_agendamento(agendamento_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    agendamento = db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return agendamento


@router.put("/{agendamento_id}")
def atualizar_agendamento(
    agendamento_id: int,
    servico_id: Optional[int] = Body(None),
    barbeiro_id: Optional[int] = Body(None),
    data_hora: Optional[str] = Body(None),
    observacoes: Optional[str] = Body(None),
    status: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_ag = db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
    if not db_ag:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    status_anterior = db_ag.status

    if data_hora or barbeiro_id is not None or servico_id is not None:
        servico_id_val = servico_id or db_ag.servico_id
        servico = db.query(Servico).filter(Servico.id == servico_id_val).first()
        if not servico:
            raise HTTPException(status_code=404, detail="Serviço não encontrado")

        try:
            data_hora_val = datetime.fromisoformat(data_hora) if data_hora else db_ag.data_hora
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data/hora inválido")
        barbeiro_id_val = barbeiro_id if barbeiro_id is not None else db_ag.barbeiro_id

        service = AgendamentoService(db)
        config = service.get_config()
        abre, hora_abre, hora_fecha = service.get_horario_funcionamento(data_hora_val.weekday())
        fim_agendamento = data_hora_val + timedelta(minutes=servico.duracao_minutos)
        minimo = agora_local()
        maximo = agora_local() + timedelta(days=config.antecedencia_maxima_dias or 30)
        if data_hora_val < minimo or data_hora_val.date() > maximo.date():
            raise HTTPException(status_code=400, detail="Agendamento fora do prazo permitido")
        if not abre or not hora_abre or not hora_fecha or data_hora_val.time() < hora_abre or fim_agendamento.time() > hora_fecha:
            raise HTTPException(status_code=400, detail="Horário fora do funcionamento do espaço")
        if service.verificar_conflito(data_hora_val, servico.duracao_minutos, barbeiro_id_val, excluir_id=agendamento_id):
            raise HTTPException(status_code=400, detail="Horário não disponível")

        if servico_id is not None:
            db_ag.duracao_minutos = servico.duracao_minutos
            db_ag.preco = servico.preco
        db_ag.servico_id = servico_id_val

    if data_hora:
        db_ag.data_hora = datetime.fromisoformat(data_hora)
    if barbeiro_id is not None:
        db_ag.barbeiro_id = barbeiro_id
    if observacoes is not None:
        db_ag.observacoes = observacoes
    if status:
        try:
            novo_status = StatusAgendamento(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Status inválido")
        if novo_status == StatusAgendamento.CONCLUIDO:
            raise HTTPException(status_code=400, detail="Use o botão Concluir dentro do horário permitido")
        db_ag.status = novo_status

    db.commit()
    db.refresh(db_ag)

    if (
        status
        and db_ag.status == StatusAgendamento.CONFIRMADO
        and status_anterior != StatusAgendamento.CONFIRMADO
    ):
        import asyncio, logging
        try:
            asyncio.run(
                notificacao_service.enviar_confirmacao_agendamento(
                    cliente_nome=db_ag.cliente.nome,
                    telefone=db_ag.cliente.telefone,
                    data_hora=db_ag.data_hora.strftime("%d/%m/%Y às %H:%M"),
                    servico=db_ag.servico.nome
                )
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Falha ao enviar confirmação do agendamento via PUT"
            )

    return db_ag


@router.patch("/{agendamento_id}/status")
def alterar_status(
    agendamento_id: int,
    status: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    try:
        novo_status = StatusAgendamento(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Status inválido")

    service = AgendamentoService(db)

    ag_existente = db.query(Agendamento).filter(
        Agendamento.id == agendamento_id
    ).first()

    if not ag_existente:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    status_anterior = ag_existente.status

    if novo_status == StatusAgendamento.CONCLUIDO:
        if status_anterior not in [
            StatusAgendamento.PENDENTE,
            StatusAgendamento.CONFIRMADO,
            StatusAgendamento.EM_ANDAMENTO
        ]:
            raise HTTPException(
                status_code=400,
                detail="Este agendamento não pode ser concluído neste status"
            )

        inicio_janela = ag_existente.data_hora
        fim_janela = inicio_janela + timedelta(
            minutes=ag_existente.duracao_minutos + 15
        )
        agora = agora_local()

        if agora < inicio_janela:
            raise HTTPException(
                status_code=400,
                detail=f"A conclusão só estará disponível a partir de {inicio_janela.strftime('%H:%M')}"
            )

        if agora > fim_janela:
            raise HTTPException(
                status_code=400,
                detail=f"O prazo para concluir terminou às {fim_janela.strftime('%H:%M')}"
            )

    ag = service.atualizar_status(agendamento_id, novo_status)

    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    import asyncio, logging

    if (
        novo_status == StatusAgendamento.CONFIRMADO
        and status_anterior != StatusAgendamento.CONFIRMADO
    ):
        try:
            asyncio.run(
                notificacao_service.enviar_confirmacao_agendamento(
                    cliente_nome=ag.cliente.nome,
                    telefone=ag.cliente.telefone,
                    data_hora=ag.data_hora.strftime("%d/%m/%Y às %H:%M"),
                    servico=ag.servico.nome
                )
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Falha ao enviar confirmação do agendamento"
            )

    elif novo_status == StatusAgendamento.CANCELADO:
        try:
            asyncio.run(notificacao_service.enviar_cancelamento_agendamento(ag))
        except Exception:
            logging.getLogger(__name__).exception("Falha ao enviar cancelamento")

    elif novo_status == StatusAgendamento.CONCLUIDO:
        from app.services.fidelidade import FidelidadeService
        fidelidade_service = FidelidadeService(db)
        fidelidade_service.processar_conclusao_agendamento(ag.id, float(ag.preco))
        db.refresh(ag)

    return ag


@router.delete("/{agendamento_id}")
def cancelar_agendamento(agendamento_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    service = AgendamentoService(db)
    ag = service.cancelar_agendamento(agendamento_id)
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    import asyncio, logging
    try:
        asyncio.run(notificacao_service.enviar_cancelamento_agendamento(ag))
    except Exception:
        logging.getLogger(__name__).exception("Falha ao enviar cancelamento")

    return {"message": "Agendamento cancelado com sucesso"}