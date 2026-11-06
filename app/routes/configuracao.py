from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional
from datetime import time
from app.database import get_db
from app.models.configuracao import ConfiguracaoBarbearia
from app.routes.auth import get_current_admin
from app.models.user import User

router = APIRouter(prefix="/configuracao", tags=["Configuração"])


@router.get("/")
def obter_configuracao(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    config = db.query(ConfiguracaoBarbearia).first()
    if not config:
        config = ConfiguracaoBarbearia()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/")
def atualizar_configuracao(
    nome_barbearia: Optional[str] = Body(None),
    telefone_contato: Optional[str] = Body(None),
    email_contato: Optional[str] = Body(None),
    endereco: Optional[str] = Body(None),
    instagram: Optional[str] = Body(None),
    whatsapp_numero: Optional[str] = Body(None),

    abre_segunda: Optional[bool] = Body(None),
    fecha_segunda: Optional[str] = Body(None),
    abre_terca: Optional[bool] = Body(None),
    fecha_terca: Optional[str] = Body(None),
    abre_quarta: Optional[bool] = Body(None),
    fecha_quarta: Optional[str] = Body(None),
    abre_quinta: Optional[bool] = Body(None),
    fecha_quinta: Optional[str] = Body(None),
    abre_sexta: Optional[bool] = Body(None),
    fecha_sexta: Optional[str] = Body(None),
    abre_sabado: Optional[bool] = Body(None),
    fecha_sabado: Optional[str] = Body(None),
    abre_domingo: Optional[bool] = Body(None),
    fecha_domingo: Optional[str] = Body(None),

    intervalo_slots_minutos: Optional[int] = Body(None),
    antecedencia_minima_horas: Optional[int] = Body(None),
    antecedencia_maxima_dias: Optional[int] = Body(None),
    permite_cancelamento_horas: Optional[int] = Body(None),

    pontos_por_real: Optional[int] = Body(None),
    pontos_corte_gratis: Optional[int] = Body(None),
    nivel_prata_pontos: Optional[int] = Body(None),
    nivel_ouro_pontos: Optional[int] = Body(None),
    nivel_diamante_pontos: Optional[int] = Body(None),

    whatsapp_lembrete_horas: Optional[int] = Body(None),
    whatsapp_confirmacao_ativa: Optional[bool] = Body(None),
    whatsapp_lembrete_ativo: Optional[bool] = Body(None),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    config = db.query(ConfiguracaoBarbearia).first()
    if not config:
        config = ConfiguracaoBarbearia()
        db.add(config)

    # Geral
    if nome_barbearia is not None:
        config.nome_barbearia = nome_barbearia
    if telefone_contato is not None:
        config.telefone_contato = telefone_contato
    if email_contato is not None:
        config.email_contato = email_contato
    if endereco is not None:
        config.endereco = endereco
    if instagram is not None:
        config.instagram = instagram
    if whatsapp_numero is not None:
        config.whatsapp_numero = whatsapp_numero

    # Horários
    for dia in ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']:
        abre = locals().get(f'abre_{dia}')
        fecha = locals().get(f'fecha_{dia}')
        if abre is not None:
            setattr(config, f'abre_{dia}', abre)
        if fecha is not None:
            try:
                setattr(config, f'fecha_{dia}', time.fromisoformat(fecha))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Formato de hora inválido para {dia}")

    # Agendamento
    if intervalo_slots_minutos is not None:
        config.intervalo_slots_minutos = intervalo_slots_minutos
    if antecedencia_minima_horas is not None:
        config.antecedencia_minima_horas = antecedencia_minima_horas
    if antecedencia_maxima_dias is not None:
        config.antecedencia_maxima_dias = antecedencia_maxima_dias
    if permite_cancelamento_horas is not None:
        config.permite_cancelamento_horas = permite_cancelamento_horas

    # Fidelidade
    if pontos_por_real is not None:
        config.pontos_por_real = pontos_por_real
    if pontos_corte_gratis is not None:
        config.pontos_corte_gratis = pontos_corte_gratis
    if nivel_prata_pontos is not None:
        config.nivel_prata_pontos = nivel_prata_pontos
    if nivel_ouro_pontos is not None:
        config.nivel_ouro_pontos = nivel_ouro_pontos
    if nivel_diamante_pontos is not None:
        config.nivel_diamante_pontos = nivel_diamante_pontos

    # WhatsApp
    if whatsapp_lembrete_horas is not None:
        config.whatsapp_lembrete_horas = whatsapp_lembrete_horas
    if whatsapp_confirmacao_ativa is not None:
        config.whatsapp_confirmacao_ativa = whatsapp_confirmacao_ativa
    if whatsapp_lembrete_ativo is not None:
        config.whatsapp_lembrete_ativo = whatsapp_lembrete_ativo

    db.commit()
    db.refresh(config)
    return config