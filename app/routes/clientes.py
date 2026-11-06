from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.cliente import Cliente
from app.routes.auth import get_current_admin

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def validar_telefone(telefone: str) -> str:
    import re
    numeros = re.sub(r'\D', '', telefone or '')
    if len(numeros) not in (10, 11):
        raise HTTPException(status_code=400, detail="Telefone deve ter 10 ou 11 dígitos")
    return numeros


def telefone_ja_cadastrado(db: Session, telefone: str, ignorar_id: int = None) -> bool:
    import re
    clientes = db.query(Cliente.id, Cliente.telefone).all()

    for cliente_id, telefone_salvo in clientes:
        if ignorar_id is not None and cliente_id == ignorar_id:
            continue

        salvo_normalizado = re.sub(r'\D', '', telefone_salvo or '')
        if salvo_normalizado == telefone:
            return True

    return False


@router.post("/", status_code=201)
def criar_cliente(
    nome: str = Body(...),
    telefone: str = Body(...),
    email: Optional[str] = Body(None),
    data_nascimento: Optional[str] = Body(None),
    observacoes: Optional[str] = Body(None),
    como_conheceu: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    telefone = validar_telefone(telefone)

    if telefone_ja_cadastrado(db, telefone):
        raise HTTPException(status_code=400, detail="Telefone já cadastrado")

    if email:
        existente_email = db.query(Cliente).filter(Cliente.email == email).first()
        if existente_email:
            raise HTTPException(status_code=400, detail="Email já cadastrado")

    data_nasc = None
    if data_nascimento:
        try:
            data_nasc = datetime.fromisoformat(data_nascimento)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido")

    db_cliente = Cliente(
        nome=nome,
        telefone=telefone,
        email=email,
        data_nascimento=data_nasc,
        observacoes=observacoes,
        como_conheceu=como_conheceu
    )
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


@router.get("/")
def listar_clientes(
    skip: int = 0,
    limit: int = 100,
    busca: Optional[str] = None,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    query = db.query(Cliente)
    if busca:
        query = query.filter(
            Cliente.nome.ilike(f"%{busca}%") |
            Cliente.telefone.ilike(f"%{busca}%") |
            Cliente.email.ilike(f"%{busca}%")
        )
    if ativo is not None:
        query = query.filter(Cliente.ativo == ativo)
    return query.offset(skip).limit(limit).all()


@router.get("/{cliente_id}")
def obter_cliente(cliente_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente


@router.put("/{cliente_id}")
def atualizar_cliente(
    cliente_id: int,
    nome: Optional[str] = Body(None),
    telefone: Optional[str] = Body(None),
    email: Optional[str] = Body(None),
    data_nascimento: Optional[str] = Body(None),
    observacoes: Optional[str] = Body(None),
    como_conheceu: Optional[str] = Body(None),
    ativo: Optional[bool] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    if telefone is not None:
        telefone = validar_telefone(telefone)
        if telefone_ja_cadastrado(db, telefone, ignorar_id=cliente_id):
            raise HTTPException(status_code=400, detail="Telefone já cadastrado")

    if email:
        existente = db.query(Cliente).filter(Cliente.email == email, Cliente.id != cliente_id).first()
        if existente:
            raise HTTPException(status_code=400, detail="Email já cadastrado")

    if nome is not None:
        db_cliente.nome = nome
    if telefone is not None:
        db_cliente.telefone = telefone
    if email is not None:
        db_cliente.email = email
    if data_nascimento is not None:
        try:
            db_cliente.data_nascimento = datetime.fromisoformat(data_nascimento)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido")
    if observacoes is not None:
        db_cliente.observacoes = observacoes
    if como_conheceu is not None:
        db_cliente.como_conheceu = como_conheceu
    if ativo is not None:
        db_cliente.ativo = ativo

    db.commit()
    db.refresh(db_cliente)
    return db_cliente


@router.delete("/{cliente_id}")
def deletar_cliente(cliente_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Preserva o cadastro, os agendamentos e o histórico de fidelidade.
    cliente.ativo = False
    db.commit()
    return {"message": "Cliente arquivado com sucesso"}