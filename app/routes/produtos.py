from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.services.fidelidade import FidelidadeService
from app.routes.auth import get_current_admin

router = APIRouter(prefix="/produtos", tags=["Produtos"])


def pontos_por_preco(preco) -> int:
    """Faixas inclusivas por valor: até 30 = 10; >30 até 50 = 15; >50 = 20."""
    valor = Decimal(str(preco or 0)).quantize(Decimal("0.01"))
    if valor <= Decimal("30.00"):
        return 10
    if valor <= Decimal("50.00"):
        return 15
    return 20


def produto_publico(produto: Produto) -> dict:
    pontos = pontos_por_preco(produto.preco)
    return {
        "id": produto.id,
        "nome": produto.nome,
        "descricao": produto.descricao,
        "preco": float(produto.preco),
        "pontos_por_compra": pontos,
        "pontos_resgate": pontos * 12,
        "ativo": produto.ativo,
    }


@router.get("/")
def listar_produtos(db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return [produto_publico(p) for p in db.query(Produto).order_by(Produto.nome).all()]


@router.post("/", status_code=201)
def criar_produto(
    nome: str = Body(...), descricao: Optional[str] = Body(None), preco: float = Body(0),
    pontos_por_compra: Optional[int] = Body(None), db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    if not nome.strip() or preco < 0:
        raise HTTPException(400, "Informe nome e preço válidos")
    produto = Produto(
        nome=nome.strip(), descricao=descricao, preco=Decimal(str(preco)),
        pontos_por_compra=pontos_por_preco(preco),
    )
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto_publico(produto)


@router.put("/{produto_id}")
def atualizar_produto(
    produto_id: int, nome: Optional[str] = Body(None), descricao: Optional[str] = Body(None),
    preco: Optional[float] = Body(None), pontos_por_compra: Optional[int] = Body(None),
    ativo: Optional[bool] = Body(None), db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    p = db.query(Produto).filter(Produto.id == produto_id).first()
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    if nome is not None and not nome.strip():
        raise HTTPException(400, "O nome do produto é obrigatório")
    if preco is not None:
        if preco < 0:
            raise HTTPException(400, "Preço não pode ser negativo")
        p.preco = Decimal(str(preco))
    if nome is not None:
        p.nome = nome.strip()
    if descricao is not None:
        p.descricao = descricao
    if ativo is not None:
        p.ativo = ativo
    # A faixa é sempre derivada do preço, inclusive para produtos antigos.
    p.pontos_por_compra = pontos_por_preco(p.preco)
    db.commit()
    db.refresh(p)
    return produto_publico(p)


@router.post("/{produto_id}/registrar-compra")
def registrar_compra(
    produto_id: int, cliente_id: int = Body(...), quantidade: int = Body(1),
    db: Session = Depends(get_db), current_user=Depends(get_current_admin),
):
    p = db.query(Produto).filter(Produto.id == produto_id, Produto.ativo.is_(True)).first()
    c = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.ativo.is_(True)).first()
    if not p:
        raise HTTPException(404, "Produto não encontrado ou inativo")
    if not c:
        raise HTTPException(404, "Cliente não encontrado")
    if quantidade < 1 or quantidade > 100:
        raise HTTPException(400, "Quantidade deve ser entre 1 e 100")
    pontos_unitarios = pontos_por_preco(p.preco)
    pontos = pontos_unitarios * quantidade
    f = FidelidadeService(db).adicionar_pontos(
        c.id, pontos, f"Compra: {p.nome} (x{quantidade}) — {pontos_unitarios} pontos/unidade"
    )
    return {
        "message": "Compra registrada", "pontos_adicionados": pontos,
        "pontos_por_unidade": pontos_unitarios, "pontos_atual": f.pontos_atual,
    }
