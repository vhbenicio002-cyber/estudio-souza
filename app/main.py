from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.config import settings
from app.database import engine
from app.routes import auth, clientes, servicos, agendamentos, fidelidade, configuracao, admin, publico, produtos
from app.services.notificacao import notificacao_service

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# Paths absolutos evitam falhas quando o servidor é iniciado fora da pasta do projeto.
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Não iniciar uma instalação de produção com credenciais conhecidas ou chave padrão.
    if not settings.DEBUG and (
        settings.SECRET_KEY == "change-this-secret-key-before-production"
        or "mude_em_producao" in settings.SECRET_KEY
        or len(settings.SECRET_KEY) < 32
        or settings.ADMIN_PASSWORD == "admin123"
        or len(settings.ADMIN_PASSWORD) < 12
    ):
        raise RuntimeError(
            "Configure SECRET_KEY (mínimo 32 caracteres) e ADMIN_PASSWORD fortes no .env antes de iniciar em produção."
        )
    # Startup seguro para migracao: nao cria nem altera dados do banco.
    logger.info("Iniciando aplicacao...")

    from sqlalchemy import inspect, text

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    tabelas_necessarias = {
        "users", "barbeiros", "clientes", "configuracao_barbearia",
        "servicos", "produtos", "agendamentos", "fidelidades",
        "transacoes_fidelidade"
    }

    tabelas_existentes = set(inspect(engine).get_table_names())
    tabelas_faltantes = tabelas_necessarias - tabelas_existentes

    if tabelas_faltantes:
        raise RuntimeError(
            "Banco incompleto. Tabelas ausentes: "
            + ", ".join(sorted(tabelas_faltantes))
        )

    logger.info("Conexao e estrutura do banco verificadas.")

    # Iniciar serviço de notificações
    if settings.ENABLE_BACKGROUND_JOBS:
        notificacao_service.start()
    else:
        logger.info("Tarefas automaticas desativadas.")

    logger.info("Aplicação iniciada com sucesso!")
    yield

    # Shutdown
    logger.info("Encerrando aplicação...")
    if settings.ENABLE_BACKGROUND_JOBS:
        notificacao_service.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de gestão para estúdio de beleza",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

# Rotas de páginas (frontend) - DEVEM vir ANTES dos routers para ter prioridade
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="public/index.html", context={"request": request})


@app.get("/agendar", response_class=HTMLResponse)
async def pagina_agendar(request: Request):
    return templates.TemplateResponse(request=request, name="public/agendar.html", context={"request": request})


@app.get("/meus-agendamentos", response_class=HTMLResponse)
async def pagina_meus_agendamentos(request: Request):
    return templates.TemplateResponse(request=request, name="public/meus_agendamentos.html", context={"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse(request=request, name="admin/login.html", context={"request": request})


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin/dashboard.html", context={"request": request})


@app.get("/admin/clientes", response_class=HTMLResponse)
async def admin_clientes(request: Request):
    return templates.TemplateResponse(request=request, name="admin/clientes.html", context={"request": request})


@app.get("/admin/agendamentos", response_class=HTMLResponse)
async def admin_agendamentos(request: Request):
    return templates.TemplateResponse(request=request, name="admin/agendamentos.html", context={"request": request})


@app.get("/admin/servicos", response_class=HTMLResponse)
async def admin_servicos(request: Request):
    return templates.TemplateResponse(request=request, name="admin/servicos.html", context={"request": request})


@app.get("/admin/fidelidade", response_class=HTMLResponse)
async def admin_fidelidade(request: Request):
    return templates.TemplateResponse(request=request, name="admin/fidelidade.html", context={"request": request})


@app.get("/fidelidade", response_class=HTMLResponse)
async def pagina_fidelidade_publica(request: Request):
    return templates.TemplateResponse(request=request, name="public/fidelidade.html", context={"request": request})


@app.get("/admin/relatorios", response_class=HTMLResponse)
async def admin_relatorios(request: Request):
    return templates.TemplateResponse(request=request, name="admin/relatorios.html", context={"request": request})


@app.get("/admin/configuracoes", response_class=HTMLResponse)
async def admin_configuracoes(request: Request):
    return templates.TemplateResponse(request=request, name="admin/configuracoes.html", context={"request": request})


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}

# Incluir routers (DEPOIS das rotas HTML para não conflitar)
app.include_router(auth.router)
app.include_router(clientes.router)
app.include_router(servicos.router)
app.include_router(agendamentos.router)
app.include_router(fidelidade.router)
app.include_router(configuracao.router)
app.include_router(admin.router)
app.include_router(publico.router)
app.include_router(produtos.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)