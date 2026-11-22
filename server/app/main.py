import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config, database, mqtt_client, telegram
from app.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db(config.DB_PATH)
    log.info("Telegram alerts %s", "on" if telegram.enabled() else "off")
    if config.MQTT_ENABLED:
        mqtt_client.start()
    yield
    if config.MQTT_ENABLED:
        mqtt_client.stop()


app = FastAPI(title="Server temperature monitor", lifespan=lifespan)
app.include_router(router)

# Montado depois da API para que "/" não capture as rotas "/api"
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
