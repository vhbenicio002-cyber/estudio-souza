from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from app.config import settings
from app.database import get_db
from app.routes.auth import get_current_admin
from app.models.user import User
from app.models.agendamento import Agendamento, StatusAgendamento
from app.models.cliente import Cliente
from app.models.servico import Servico
from app.models.fidelidade import Fidelidade

router = APIRouter(prefix="/admin", tags=["Admin - Dashboard"])


@router.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    agora_local = datetime.now(ZoneInfo(settings.TIMEZONE)).replace(tzinfo=None)
    hoje = agora_local.date()
    inicio_mes = date(hoje.year, hoje.month, 1)
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    # Agendamentos hoje
    agendamentos_hoje = db.query(Agendamento).filter(
        Agendamento.data_hora >= datetime.combine(hoje, datetime.min.time()),
        Agendamento.data_hora < datetime.combine(hoje + timedelta(days=1), datetime.min.time()),
    ).count()

    # Agendamentos esta semana
    agendamentos_semana = db.query(Agendamento).filter(
        Agendamento.data_hora >= datetime.combine(inicio_semana, datetime.min.time()),
        Agendamento.data_hora < datetime.combine(inicio_semana + timedelta(days=7), datetime.min.time()),
    ).count()

    # Agendamentos este mês
    agendamentos_mes = db.query(Agendamento).filter(
        Agendamento.data_hora >= datetime.combine(inicio_mes, datetime.min.time()),
    ).count()

    # Faturamento
    faturamento_hoje = db.query(func.coalesce(func.sum(Agendamento.preco), 0)).filter(
        Agendamento.status == StatusAgendamento.CONCLUIDO,
        Agendamento.concluido_em >= datetime.combine(hoje, datetime.min.time()),
        Agendamento.concluido_em < datetime.combine(hoje + timedelta(days=1), datetime.min.time()),
    ).scalar()

    faturamento_mes = db.query(func.coalesce(func.sum(Agendamento.preco), 0)).filter(
        Agendamento.status == StatusAgendamento.CONCLUIDO,
        Agendamento.concluido_em >= datetime.combine(inicio_mes, datetime.min.time()),
    ).scalar()

    # Clientes
    total_clientes = db.query(Cliente).filter(Cliente.ativo == True).count()
    novos_clientes_mes = db.query(Cliente).filter(
        Cliente.ativo == True,
        Cliente.criado_em >= datetime.combine(inicio_mes, datetime.min.time()),
    ).count()

    # Serviços mais populares (mês)
    servicos_populares = db.query(
        Servico.nome,
        func.count(Agendamento.id).label("total")
    ).join(Agendamento).filter(
        Agendamento.data_hora >= datetime.combine(inicio_mes, datetime.min.time()),
        Agendamento.status.notin_([StatusAgendamento.CANCELADO, StatusAgendamento.NAO_COMPARECEU]),
    ).group_by(Servico.id).order_by(func.count(Agendamento.id).desc()).limit(5).all()

    # Próximos agendamentos
    proximos = db.query(Agendamento).filter(
        Agendamento.status.in_([StatusAgendamento.PENDENTE, StatusAgendamento.CONFIRMADO, StatusAgendamento.EM_ANDAMENTO]),
        Agendamento.data_hora >= agora_local,
    ).order_by(Agendamento.data_hora).limit(10).all()

    return {
        "resumo": {
            "agendamentos_hoje": agendamentos_hoje,
            "agendamentos_semana": agendamentos_semana,
            "agendamentos_mes": agendamentos_mes,
            "faturamento_hoje": float(faturamento_hoje or 0),
            "faturamento_mes": float(faturamento_mes or 0),
            "total_clientes": total_clientes,
            "novos_clientes_mes": novos_clientes_mes,
        },
        "servicos_populares": [
            {"servico": s.nome, "total": s.total} for s in servicos_populares
        ],
        "proximos_agendamentos": [
            {
                "id": a.id,
                "cliente": a.cliente.nome,
                "servico": a.servico.nome,
                "data_hora": a.data_hora.isoformat(),
                "atendimento": "Individual",
                "status": a.status.value,
                "preco": float(a.preco or 0),
            } for a in proximos
        ],
    }


@router.get("/relatorio/faturamento")
def relatorio_faturamento(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    if data_inicio > data_fim:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="A data inicial não pode ser posterior à data final")

    # Faturamento por dia
    faturamento_diario = db.query(
        func.date(Agendamento.concluido_em).label("data"),
        func.count(Agendamento.id).label("quantidade"),
        func.coalesce(func.sum(Agendamento.preco), 0).label("total")
    ).filter(
        Agendamento.status == StatusAgendamento.CONCLUIDO,
        Agendamento.concluido_em >= datetime.combine(data_inicio, datetime.min.time()),
        Agendamento.concluido_em <= datetime.combine(data_fim, datetime.max.time()),
    ).group_by(func.date(Agendamento.concluido_em)).order_by(func.date(Agendamento.concluido_em)).all()

    clientes_atendidos = db.query(
        func.count(func.distinct(Agendamento.cliente_id))
    ).filter(
        Agendamento.status == StatusAgendamento.CONCLUIDO,
        Agendamento.concluido_em >= datetime.combine(data_inicio, datetime.min.time()),
        Agendamento.concluido_em <= datetime.combine(data_fim, datetime.max.time()),
    ).scalar() or 0

    # Faturamento por serviço
    faturamento_servico = db.query(
        Servico.nome,
        func.count(Agendamento.id).label("quantidade"),
        func.coalesce(func.sum(Agendamento.preco), 0).label("total")
    ).join(Agendamento).filter(
        Agendamento.status == StatusAgendamento.CONCLUIDO,
        Agendamento.concluido_em >= datetime.combine(data_inicio, datetime.min.time()),
        Agendamento.concluido_em <= datetime.combine(data_fim, datetime.max.time()),
    ).group_by(Servico.id).order_by(func.coalesce(func.sum(Agendamento.preco), 0).desc()).all()

    return {
        "periodo": {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
        "clientes_atendidos": int(clientes_atendidos),
        "por_dia": [
            {"data": str(d.data), "quantidade": d.quantidade, "total": float(d.total)}
            for d in faturamento_diario
        ],
        "por_servico": [
            {"servico": s.nome, "quantidade": s.quantidade, "total": float(s.total)}
            for s in faturamento_servico
        ],
        "por_barbeiro": [],
    }


@router.get("/relatorio/horarios-pico")
def relatorio_horarios_pico(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    if data_inicio > data_fim:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="A data inicial não pode ser posterior à data final")

    horarios = db.query(
        func.extract("hour", Agendamento.data_hora).label("hora"),
        func.count(Agendamento.id).label("total")
    ).filter(
        Agendamento.data_hora >= datetime.combine(data_inicio, datetime.min.time()),
        Agendamento.data_hora <= datetime.combine(data_fim, datetime.max.time()),
        Agendamento.status.in_([StatusAgendamento.CONFIRMADO, StatusAgendamento.CONCLUIDO, StatusAgendamento.EM_ANDAMENTO]),
    ).group_by(func.extract("hour", Agendamento.data_hora)).order_by(func.extract("hour", Agendamento.data_hora)).all()

    return {
        "periodo": {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
        "horarios": [
            {"hora": f"{int(h.hora):02d}:00", "agendamentos": h.total} for h in horarios
        ]
    }