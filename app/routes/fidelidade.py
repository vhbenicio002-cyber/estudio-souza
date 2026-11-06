from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.fidelidade import FidelidadeService
from app.services.notificacao import notificacao_service
from app.routes.auth import get_current_admin
from app.models.user import User
from app.models.fidelidade import Fidelidade

router = APIRouter(prefix="/fidelidade", tags=["Fidelidade"])


@router.get("/cliente/{cliente_id}")
def obter_fidelidade(cliente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    service = FidelidadeService(db)
    fidelidade = service.get_or_create_fidelidade(cliente_id)
    return fidelidade


@router.get("/cliente/{cliente_id}/extrato")
def extrato_fidelidade(cliente_id: int, limite: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    service = FidelidadeService(db)
    return service.get_extrato(cliente_id, limite)


@router.post("/cliente/{cliente_id}/resgatar")
def resgatar_pontos(
    cliente_id: int,
    pontos: int = Body(...),
    descricao: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    from app.models.cliente import Cliente
    if not db.query(Cliente).filter(Cliente.id == cliente_id).first():
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    service = FidelidadeService(db)
    try:
        fidelidade = service.resgatar_pontos(cliente_id, pontos, descricao or "Resgate de pontos")

        import asyncio, logging
        try:
            asyncio.run(notificacao_service.enviar_fidelidade_resgatada(cliente_id, pontos, descricao or "Recompensa"))
        except Exception:
            logging.getLogger(__name__).exception("Falha ao enviar notificação de fidelidade")

        return {"message": "Pontos resgatados com sucesso", "pontos_restantes": fidelidade.pontos_atual}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cliente/{cliente_id}/corte-gratis")
def resgatar_corte_gratis(cliente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    from app.models.cliente import Cliente
    if not db.query(Cliente).filter(Cliente.id == cliente_id).first():
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    service = FidelidadeService(db)
    if not service.pode_resgatar_corte_gratis(cliente_id):
        raise HTTPException(status_code=400, detail="Pontos insuficientes para serviço grátis")

    config = service.get_config()
    fidelidade = service.resgatar_pontos(cliente_id, config.pontos_corte_gratis, "Serviço grátis (fidelidade)")

    import asyncio, logging
    try:
        asyncio.run(notificacao_service.enviar_fidelidade_resgatada(cliente_id, config.pontos_corte_gratis, "Serviço grátis"))
    except Exception:
        logging.getLogger(__name__).exception("Falha ao enviar notificação de fidelidade")

    return {"message": "Serviço grátis resgatado!", "pontos_restantes": fidelidade.pontos_atual}


@router.get("/ranking")
def ranking_fidelidade(
    limite: int = 100,
    busca: Optional[str] = None,
    nivel: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    from app.models.fidelidade import Fidelidade
    from app.models.cliente import Cliente

    query = db.query(
        Fidelidade.cliente_id,
        Fidelidade.pontos_atual,
        Fidelidade.pontos_total_ganho,
        Fidelidade.nivel,
        Cliente.nome,
        Cliente.telefone
    ).join(Cliente)

    if busca:
        query = query.filter(
            Cliente.nome.ilike(f"%{busca}%") |
            Cliente.telefone.ilike(f"%{busca}%")
        )
    if nivel:
        query = query.filter(Fidelidade.nivel == nivel)

    resultados = query.order_by(Fidelidade.pontos_total_ganho.desc()).limit(limite).all()

    return [
        {
            "cliente_id": r.cliente_id,
            "nome": r.nome,
            "telefone": r.telefone,
            "pontos_atual": r.pontos_atual,
            "pontos_total": r.pontos_total_ganho,
            "nivel": r.nivel
        }
        for r in resultados
    ]


def _cliente_publico_por_identificacao(db: Session, nome: str, telefone: str):
    import re
    nome_limpo = " ".join((nome or "").strip().lower().split())
    tel = re.sub(r"\D", "", telefone or "")
    if not nome_limpo or len(tel) not in (10, 11):
        raise HTTPException(status_code=400, detail="Informe nome completo e telefone válido")
    from app.models.cliente import Cliente
    clientes = db.query(Cliente).filter(Cliente.ativo == True).all()
    for cliente in clientes:
        if " ".join(cliente.nome.strip().lower().split()) == nome_limpo and re.sub(r"\D", "", cliente.telefone) == tel:
            return cliente
    raise HTTPException(status_code=404, detail="Não encontramos cadastro com esses dados")


@router.get("/consulta-publica")
def consulta_fidelidade_publica(nome: str, telefone: str, db: Session = Depends(get_db)):
    from app.models.servico import Servico
    from app.models.produto import Produto
    from app.routes.produtos import produto_publico
    cliente = _cliente_publico_por_identificacao(db, nome, telefone)
    f = db.query(Fidelidade).filter_by(cliente_id=cliente.id).first()
    pontos = f.pontos_atual if f else 0
    servicos = db.query(Servico).filter(Servico.ativo == True, Servico.pontos_resgate > 0).order_by(Servico.pontos_resgate, Servico.nome).all()
    produtos = [produto_publico(p) for p in db.query(Produto).filter(Produto.ativo.is_(True)).order_by(Produto.nome).all()]
    produtos_disponiveis = [p for p in produtos if pontos >= p["pontos_resgate"]]
    produtos_indisponiveis = [p for p in produtos if pontos < p["pontos_resgate"]]
    return {
        "cliente": cliente.nome,
        "pontos_atual": pontos,
        "recompensas": [{"id": s.id, "nome": s.nome, "pontos": s.pontos_resgate} for s in servicos if pontos >= s.pontos_resgate],
        "servicos_indisponiveis": [{"id": s.id, "nome": s.nome, "pontos": s.pontos_resgate} for s in servicos if pontos < s.pontos_resgate],
        "produtos_disponiveis": produtos_disponiveis,
        "produtos_indisponiveis": produtos_indisponiveis,
    }


@router.post("/resgatar-publico")
def resgatar_fidelidade_publico(
    nome: str = Body(...), telefone: str = Body(...), servico_id: int = Body(...),
    db: Session = Depends(get_db)
):
    from app.models.servico import Servico
    cliente = _cliente_publico_por_identificacao(db, nome, telefone)
    servico = db.query(Servico).filter(Servico.id == servico_id, Servico.ativo == True).first()
    if not servico or servico.pontos_resgate <= 0:
        raise HTTPException(status_code=404, detail="Recompensa não encontrada ou indisponível")
    try:
        f = FidelidadeService(db).resgatar_pontos(cliente.id, servico.pontos_resgate, f"Resgate de recompensa: {servico.nome}")
        return {"message": f"Resgate de {servico.nome} realizado! Entre em contato com o Estúdio Souza para agendar.", "pontos_restantes": f.pontos_atual, "servico": servico.nome}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resgatar-produtos-publico")
def resgatar_produtos_publico(
    nome: str = Body(...), telefone: str = Body(...), itens: list[dict] = Body(...),
    db: Session = Depends(get_db),
):
    from app.models.produto import Produto
    from app.routes.produtos import pontos_por_preco

    cliente = _cliente_publico_por_identificacao(db, nome, telefone)
    if not isinstance(itens, list) or not itens:
        raise HTTPException(status_code=400, detail="Selecione ao menos um produto")

    quantidades = {}
    for item in itens:
        try:
            produto_id = int(item.get("produto_id"))
            quantidade = int(item.get("quantidade"))
        except (TypeError, ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Produto ou quantidade inválidos")
        if quantidade < 1 or quantidade > 100:
            raise HTTPException(status_code=400, detail="Cada quantidade deve ser entre 1 e 100")
        total_produto = quantidades.get(produto_id, 0) + quantidade
        if total_produto > 100:
            raise HTTPException(status_code=400, detail="A quantidade total de cada produto não pode ultrapassar 100 unidades")
        quantidades[produto_id] = total_produto

    produtos = db.query(Produto).filter(
        Produto.id.in_(list(quantidades)), Produto.ativo.is_(True)
    ).all()
    por_id = {p.id: p for p in produtos}
    if len(por_id) != len(quantidades):
        raise HTTPException(status_code=404, detail="Um ou mais produtos não estão disponíveis")

    total_pontos = 0
    detalhes = []
    for produto_id, quantidade in quantidades.items():
        produto = por_id[produto_id]
        pontos_unidade = pontos_por_preco(produto.preco) * 12
        total_pontos += pontos_unidade * quantidade
        detalhes.append(f"{produto.nome} (x{quantidade}) — {pontos_unidade * quantidade} pts")

    try:
        fidelidade = FidelidadeService(db).resgatar_pontos(
            cliente.id, total_pontos, "Resgate de produtos: " + "; ".join(detalhes)
        )
        return {
            "message": "Resgate realizado! Entre em contato com o Estúdio Souza para combinar a retirada.",
            "pontos_resgatados": total_pontos,
            "pontos_restantes": fidelidade.pontos_atual,
            "itens": detalhes,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
