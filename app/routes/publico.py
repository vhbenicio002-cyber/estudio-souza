from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
from app.database import get_db
from app.models.cliente import Cliente
from app.models.servico import Servico
from app.models.agendamento import Agendamento, StatusAgendamento
from app.models.configuracao import ConfiguracaoBarbearia
from app.schemas.agendamento import SlotDisponivel
from app.services.agendamento import AgendamentoService, agora_local
from app.services.notificacao import notificacao_service

router = APIRouter(prefix="/publico", tags=["Público - Agendamento"])


@router.get("/config")
def obter_config_publico(db: Session = Depends(get_db)):
    config = db.query(ConfiguracaoBarbearia).first()
    if not config:
        config = ConfiguracaoBarbearia()
        db.add(config)
        db.commit()
        db.refresh(config)

    return {
        "nome_barbearia": config.nome_barbearia,
        "telefone_contato": config.telefone_contato,
        "email_contato": config.email_contato,
        "endereco": config.endereco,
        "instagram": config.instagram,
        "whatsapp_numero": config.whatsapp_numero,
        "intervalo_slots_minutos": config.intervalo_slots_minutos,
        "antecedencia_minima_horas": config.antecedencia_minima_horas,
        "antecedencia_maxima_dias": config.antecedencia_maxima_dias,
    }


@router.get("/servicos")
def listar_servicos_publico(categoria: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Servico).filter(Servico.ativo == True)
    if categoria:
        query = query.filter(Servico.categoria == categoria)
    servicos = query.order_by(Servico.ordem, Servico.nome).all()

    return [
        {
            "id": s.id,
            "nome": s.nome,
            "descricao": s.descricao,
            "preco": float(s.preco),
            "duracao_minutos": s.duracao_minutos,
            "categoria": s.categoria,
            "pontos_resgate": s.pontos_resgate,
        }
        for s in servicos
    ]


@router.get("/categorias")
def listar_categorias_publico(db: Session = Depends(get_db)):
    categorias = db.query(Servico.categoria).filter(
        Servico.ativo == True,
        Servico.categoria.isnot(None)
    ).distinct().all()
    return [c[0] for c in categorias if c[0]]


@router.get("/barbeiros")
def listar_barbeiros_publico():
    """Compatibilidade com clientes antigos: o espaço possui agenda única."""
    return []


@router.get("/slots")
def slots_disponiveis_publico(
    data: str,
    servico_id: Optional[int] = None,
    barbeiro_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        dt = datetime.strptime(data, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido")

    config = AgendamentoService(db).get_config()

    agora = agora_local()
    min_data = agora.date()
    max_data = (agora + timedelta(days=config.antecedencia_maxima_dias or 30)).date()

    if dt < min_data:
        raise HTTPException(status_code=400, detail=f"Agendamento só pode ser feito a partir de {config.antecedencia_minima_horas}h de antecedência")
    if dt > max_data:
        raise HTTPException(status_code=400, detail=f"Agendamento só pode ser feito até {config.antecedencia_maxima_dias} dias de antecedência")

    service = AgendamentoService(db)
    return service.get_slots_disponiveis(dt, barbeiro_id, servico_id)


@router.post("/agendar")
def agendar_publico(
    nome: str = Body(...),
    telefone: str = Body(...),
    email: Optional[str] = Body(None),
    servico_id: int = Body(...),
    data_hora: str = Body(...),
    barbeiro_id: Optional[int] = Body(None),
    observacoes: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    try:
        dt = datetime.fromisoformat(data_hora)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data/hora inválido")

    # Validar telefone
    import re
    numeros = re.sub(r'\D', '', telefone)
    if len(numeros) < 10 or len(numeros) > 11:
        raise HTTPException(status_code=400, detail="Telefone inválido")

    # Carregar/criar configurações antes de inserir cliente, mantendo a operação atômica.
    service = AgendamentoService(db)
    service.get_config()

    # Normalizar telefone
    telefone_limpo = ''.join(filter(str.isdigit, telefone))

    # Buscar ou criar cliente (normalizando telefone do banco)
    clientes = db.query(Cliente).all()
    cliente = None
    for c in clientes:
        c_tel = ''.join(filter(str.isdigit, c.telefone))
        if c_tel == telefone_limpo:
            cliente = c
            break

    if not cliente:
        cliente = Cliente(
            nome=nome,
            telefone=telefone,
            email=email,
        )
        db.add(cliente)
        db.flush()
    else:
        if cliente.nome != nome:
            cliente.nome = nome
        if email and cliente.email != email:
            cliente.email = email

    # Criar agendamento
    try:
        agendamento = service.criar_agendamento(
            cliente_id=cliente.id,
            servico_id=servico_id,
            data_hora=dt,
            barbeiro_id=barbeiro_id,
            observacoes=observacoes,
        )

        import asyncio, logging
        try:
            asyncio.run(
                notificacao_service.enviar_solicitacao_agendamento(
                    cliente_nome=agendamento.cliente.nome,
                    telefone=agendamento.cliente.telefone,
                    data_hora=agendamento.data_hora.strftime("%d/%m/%Y às %H:%M"),
                    servico=agendamento.servico.nome
                )
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Falha ao enviar mensagem de solicitação de agendamento"
            )

        return {
            "success": True,
            "message": "Agendamento realizado com sucesso!",
            "agendamento_id": agendamento.id,
            "data_hora": agendamento.data_hora.isoformat(),
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise


@router.get("/agendamentos")
def listar_agendamentos_por_telefone(telefone: str, db: Session = Depends(get_db)):
    # Normalizar telefone: remover não-dígitos
    telefone_limpo = ''.join(filter(str.isdigit, telefone))

    # Buscar cliente normalizando telefone do banco também
    clientes = db.query(Cliente).all()
    cliente = None
    for c in clientes:
        c_tel = ''.join(filter(str.isdigit, c.telefone))
        if c_tel == telefone_limpo:
            cliente = c
            break

    if not cliente:
        return []

    agendamentos = db.query(Agendamento).filter(
        Agendamento.cliente_id == cliente.id
    ).order_by(Agendamento.data_hora.desc()).all()

    return [
        {
            "id": a.id,
            "servico": a.servico.nome,
            "data_hora": a.data_hora.isoformat(),
            "barbeiro": a.barbeiro.user.nome if a.barbeiro and a.barbeiro.user else None,
            "status": a.status.value,
            "preco": float(a.preco),
        }
        for a in agendamentos
    ]


@router.get("/agendamento/{agendamento_id}")
def consultar_agendamento_publico(agendamento_id: int, telefone: str, db: Session = Depends(get_db)):
    agendamento = db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
    telefone_limpo = ''.join(filter(str.isdigit, telefone))
    cliente_tel = ''.join(filter(str.isdigit, agendamento.cliente.telefone)) if agendamento else ""

    if not agendamento or cliente_tel != telefone_limpo:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    return {
        "id": agendamento.id,
        "servico": agendamento.servico.nome,
        "data_hora": agendamento.data_hora.isoformat(),
        "barbeiro": agendamento.barbeiro.user.nome if agendamento.barbeiro and agendamento.barbeiro.user else "Não definido",
        "status": agendamento.status.value,
        "preco": float(agendamento.preco),
    }


@router.delete("/agendamento/{agendamento_id}")
def cancelar_agendamento_publico(agendamento_id: int, telefone: str, db: Session = Depends(get_db)):
    config = AgendamentoService(db).get_config()

    # Normalizar telefone
    telefone_limpo = ''.join(filter(str.isdigit, telefone))

    agendamento = db.query(Agendamento).filter(
        Agendamento.id == agendamento_id
    ).first()

    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Verificar telefone do cliente (normalizado)
    cliente_tel = ''.join(filter(str.isdigit, agendamento.cliente.telefone))
    if cliente_tel != telefone_limpo:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    horas_antecedencia = (agendamento.data_hora - datetime.now()).total_seconds() / 3600
    if horas_antecedencia < config.permite_cancelamento_horas:
        raise HTTPException(
            status_code=400,
            detail=f"Cancelamento só permitido com {config.permite_cancelamento_horas}h de antecedência"
        )

    service = AgendamentoService(db)
    ag = service.cancelar_agendamento(agendamento_id)

    import asyncio, logging
    try:
        asyncio.run(notificacao_service.enviar_cancelamento_agendamento(ag))
    except Exception:
        logging.getLogger(__name__).exception("Falha ao enviar cancelamento")

    return {"message": "Agendamento cancelado com sucesso"}