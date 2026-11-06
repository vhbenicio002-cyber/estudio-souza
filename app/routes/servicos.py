from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from app.database import get_db
from app.models.servico import Servico
from app.routes.auth import get_current_admin

router = APIRouter(prefix="/servicos", tags=["Serviços"])


@router.post("/", status_code=201)
def criar_servico(
    nome: str = Body(...),
    descricao: Optional[str] = Body(None),
    preco: float = Body(...),
    duracao_minutos: int = Body(...),
    categoria: Optional[str] = Body(None),
    ordem: int = Body(0),
    pontos_resgate: int = Body(0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    if preco < 0:
        raise HTTPException(status_code=400, detail="Preço não pode ser negativo")
    if pontos_resgate < 0:
        raise HTTPException(status_code=400, detail="Pontos para resgate não podem ser negativos")
    if duracao_minutos <= 0 or duracao_minutos > 480:
        raise HTTPException(status_code=400, detail="Duração deve ser entre 1 e 480 minutos")

    db_servico = Servico(
        nome=nome,
        descricao=descricao,
        preco=Decimal(str(preco)),
        duracao_minutos=duracao_minutos,
        categoria=categoria,
        ordem=ordem,
        pontos_resgate=pontos_resgate
    )
    db.add(db_servico)
    db.commit()
    db.refresh(db_servico)
    return db_servico


@router.get("/")
def listar_servicos(
    skip: int = 0,
    limit: int = 100,
    busca: Optional[str] = None,
    categoria: Optional[str] = None,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    query = db.query(Servico)
    if busca:
        query = query.filter(
            Servico.nome.ilike(f"%{busca}%") |
            Servico.categoria.ilike(f"%{busca}%")
        )
    if categoria:
        query = query.filter(Servico.categoria == categoria)
    if ativo is not None:
        query = query.filter(Servico.ativo == ativo)
    return query.order_by(Servico.ordem, Servico.nome).offset(skip).limit(limit).all()


@router.get("/publico")
def listar_servicos_publico(
    categoria: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Servico).filter(Servico.ativo == True)
    if categoria:
        query = query.filter(Servico.categoria == categoria)
    return query.order_by(Servico.ordem, Servico.nome).all()


@router.get("/categorias")
def listar_categorias(db: Session = Depends(get_db)):
    categorias = db.query(Servico.categoria).filter(Servico.categoria.isnot(None)).distinct().all()
    return [c[0] for c in categorias if c[0]]


@router.get("/{servico_id}")
def obter_servico(servico_id: int, db: Session = Depends(get_db)):
    servico = db.query(Servico).filter(Servico.id == servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return servico


@router.put("/{servico_id}")
def atualizar_servico(
    servico_id: int,
    nome: Optional[str] = Body(None),
    descricao: Optional[str] = Body(None),
    preco: Optional[float] = Body(None),
    duracao_minutos: Optional[int] = Body(None),
    categoria: Optional[str] = Body(None),
    ordem: Optional[int] = Body(None),
    ativo: Optional[bool] = Body(None),
    pontos_resgate: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    db_servico = db.query(Servico).filter(Servico.id == servico_id).first()
    if not db_servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    if preco is not None:
        if preco < 0:
            raise HTTPException(status_code=400, detail="Preço não pode ser negativo")
        db_servico.preco = Decimal(str(preco))

    if duracao_minutos is not None:
        if duracao_minutos <= 0 or duracao_minutos > 480:
            raise HTTPException(status_code=400, detail="Duração deve ser entre 1 e 480 minutos")
        db_servico.duracao_minutos = duracao_minutos

    if pontos_resgate is not None:
        if pontos_resgate < 0:
            raise HTTPException(status_code=400, detail="Pontos para resgate não podem ser negativos")
        db_servico.pontos_resgate = pontos_resgate

    if nome is not None:
        db_servico.nome = nome
    if descricao is not None:
        db_servico.descricao = descricao
    if categoria is not None:
        db_servico.categoria = categoria
    if ordem is not None:
        db_servico.ordem = ordem
    if ativo is not None:
        db_servico.ativo = ativo

    db.commit()
    db.refresh(db_servico)
    return db_servico


@router.delete("/{servico_id}")
def deletar_servico(servico_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    servico = db.query(Servico).filter(Servico.id == servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    servico.ativo = False
    db.commit()
    return {"message": "Serviço desativado com sucesso"}