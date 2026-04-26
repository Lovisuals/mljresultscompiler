import asyncio
import logging
import signal
import threading
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings, validate_settings

try:
    from src.session_storage import get_session_db
    SESSION_STORAGE_AVAILABLE = True
except ImportError:
    SESSION_STORAGE_AVAILABLE = False

try:
    from src.async_ai_service import initialize_async_ai, shutdown_async_ai
    AI_SERVICE_AVAILABLE = True
except ImportError:
    AI_SERVICE_AVAILABLE = False

try:
    from src.async_data_agent import initialize_async_data_agent, shutdown_async_data_agent
    DATA_AGENT_AVAILABLE = True
except ImportError:
    DATA_AGENT_AVAILABLE = False

try:
    from src.async_file_io import initialize_async_file_io, shutdown_async_file_io
    FILE_IO_AVAILABLE = True
except ImportError:
    FILE_IO_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot_thread = None
bot_lock = threading.Lock()
bot_initialized = False

cm_bot_thread = None
cm_bot_lock = threading.Lock()
cm_bot_initialized = False

is_shutting_down = False

def start_bot_thread():
    global bot_thread, bot_initialized

    settings = get_settings()
    if not settings.ENABLE_TELEGRAM_BOT:
        return None

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        return None

    with bot_lock:
        if bot_initialized and bot_thread and bot_thread.is_alive():
            return bot_thread
        bot_initialized = True

    def bot_worker():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path='.env')

            try:
                from telegram_bot import build_application
                from telegram import Update
                from telegram.error import Conflict, NetworkError, TelegramError
            except Exception as e:
                logger.error(f"Bot initialization failed: {e}")
                return

            token = os.getenv('TELEGRAM_BOT_TOKEN')
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def run_bot_with_retry():
                retry_count = 0
                max_retries = 30

                while retry_count < max_retries:
                    application = None
                    try:
                        application = build_application(token)
                        await application.initialize()
                        try:
                            await application.bot.delete_webhook(drop_pending_updates=True)
                        except:
                            pass
                        await application.start()
                        await application.updater.start_polling(
                            allowed_updates=Update.ALL_TYPES,
                            drop_pending_updates=True
                        )
                        stop_event = asyncio.Event()
                        async def check_shutdown():
                            while not is_shutting_down and application.updater and application.updater.running:
                                await asyncio.sleep(1)
                            stop_event.set()
                        asyncio.create_task(check_shutdown())
                        await stop_event.wait()
                        if is_shutting_down:
                            await application.updater.stop()
                            await application.stop()
                            await application.shutdown()
                            return False
                        else:
                            await application.updater.stop()
                            await application.stop()
                            await application.shutdown()
                            await asyncio.sleep(10)
                            return True
                    except (Conflict, TelegramError, NetworkError) as e:
                        retry_count += 1
                        await asyncio.sleep(min(2 ** retry_count, 60))
                        if application:
                            try:
                                await application.shutdown()
                            except: pass
                    except Exception as e:
                        retry_count += 1
                        await asyncio.sleep(10)
                return True

            async def run_bot_forever():
                while True:
                    if not await run_bot_with_retry(): break
                    await asyncio.sleep(60)

            try:
                loop.run_until_complete(run_bot_forever())
            finally:
                loop.close()
        finally:
            global bot_initialized
            with bot_lock:
                bot_initialized = False

    thread = threading.Thread(target=bot_worker, daemon=True)
    thread.start()
    return thread

def start_cm_bot_thread():
    global cm_bot_thread, cm_bot_initialized
    settings = get_settings()
    token = settings.MLJCM_BOT_TOKEN or os.getenv('MLJCM_BOT_TOKEN')
    if not token:
        return None
    with cm_bot_lock:
        if cm_bot_initialized and cm_bot_thread and cm_bot_thread.is_alive():
            return cm_bot_thread
        cm_bot_initialized = True

    def cm_worker():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path='.env')
            try:
                from content_manager.cm_bot import ContentManagerBot
                from content_manager.storage import CMStorage
            except:
                return
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def run_cm_bot():
                try:
                    storage = CMStorage()
                    cm_bot = ContentManagerBot(token=token, storage=storage)
                    await cm_bot.initialize()
                    await cm_bot.start_polling()
                    while not is_shutting_down:
                        await asyncio.sleep(1)
                    await cm_bot.shutdown()
                except:
                    pass
            loop.run_until_complete(run_cm_bot())
        finally:
            global cm_bot_initialized
            with cm_bot_lock:
                cm_bot_initialized = False

    cm_bot_thread = threading.Thread(target=cm_worker, daemon=True)
    cm_bot_thread.start()
    return cm_bot_thread

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_thread, cm_bot_thread, is_shutting_down
    try:
        validate_settings()
        if AI_SERVICE_AVAILABLE: await initialize_async_ai()
        if DATA_AGENT_AVAILABLE: await initialize_async_data_agent()
        if FILE_IO_AVAILABLE: await initialize_async_file_io()
        bot_thread = start_bot_thread()
        cm_bot_thread = start_cm_bot_thread()
        def signal_handler(sig, frame):
            global is_shutting_down
            is_shutting_down = True
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except Exception as e:
        logger.error(f"Startup error: {e}")
    yield
    is_shutting_down = True
    if AI_SERVICE_AVAILABLE: await shutdown_async_ai()
    if DATA_AGENT_AVAILABLE: await shutdown_async_data_agent()
    if FILE_IO_AVAILABLE: await shutdown_async_file_io()

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["https://mljresultscompiler.onrender.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}

    @app.get("/ping")
    async def ping():
        return {"status": "pong"}

    try:
        from src.web_ui_clean import router as web_ui_router
        app.include_router(web_ui_router)
    except: pass

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
