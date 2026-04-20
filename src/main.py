#!/usr/bin/env python
"""
MLJ Results Compiler - Main Entrypoint
Handles application startup, shutdown, and orchestration.

Single entry point for all deployment modes (web, bot, combined).
Replaces: server.py (merged here)
"""

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
from src.session_storage import get_session_db
from src.async_ai_service import initialize_async_ai, shutdown_async_ai
from src.async_data_agent import initialize_async_data_agent, shutdown_async_data_agent
from src.async_file_io import initialize_async_file_io, shutdown_async_file_io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global bot thread and state
bot_thread = None
bot_lock = threading.Lock()
bot_initialized = False

# Content Manager bot thread and state
cm_bot_thread = None
cm_bot_lock = threading.Lock()
cm_bot_initialized = False

is_shutting_down = False


def start_bot_thread():
    global bot_thread, bot_initialized

    
    settings = get_settings()
    if not settings.ENABLE_TELEGRAM_BOT:
        logger.info("Telegram bot disabled (ENABLE_TELEGRAM_BOT=false)")
        return None
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, bot will not start")
        return None
    
    with bot_lock:
        if bot_initialized and bot_thread and bot_thread.is_alive():
            logger.warning("Bot already running, skipping duplicate")
            return bot_thread
        bot_initialized = True
    
    def bot_worker():
        try:
            from dotenv import load_dotenv
            
            logger.info("Initializing Telegram bot in background thread...")
            
            load_dotenv(dotenv_path='.env')
            

            try:
                from telegram_bot import build_application
                from telegram import Update
                from telegram.error import Conflict, NetworkError, TelegramError
            except Exception as e:
                logger.error(f"Failed to import telegram_bot: {e}", exc_info=True)
                return
            
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN not available in bot thread")
                return
            
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
                        logger.info("Bot initialized")
                        
                        try:
                            await application.bot.delete_webhook(drop_pending_updates=True)
                        except Exception:
                            pass
                        
                        logger.info("Starting bot polling...")
                        await application.start()
                        await application.updater.start_polling(
                            allowed_updates=Update.ALL_TYPES,
                            drop_pending_updates=True
                        )
                        logger.info("Bot is now polling for updates")
                        
                        stop_event = asyncio.Event()
                        
                        async def check_shutdown():
                            while not is_shutting_down and application.updater and application.updater.running:
                                await asyncio.sleep(1)
                            stop_event.set()
                            
                        asyncio.create_task(check_shutdown())
                        await stop_event.wait()
                            
                        if is_shutting_down:
                            logger.info("Shutting down bot gracefully...")
                            await application.updater.stop()
                            await application.stop()
                            await application.shutdown()
                            return False
                        else:
                            logger.warning("Bot polling stopped unexpectedly. Preparing to restart...")
                            try:
                                await application.updater.stop()
                                await application.stop()
                                await application.shutdown()
                            except Exception:
                                pass
                            
                            await asyncio.sleep(10)
                            return True
                        
                    except Conflict as e:
                        retry_count += 1
                        wait_time = 30 if retry_count <= 3 else min(5 ** min(retry_count - 3, 4), 120)
                        logger.error(f"Bot conflict #{retry_count}/{max_retries}: {e}")
                        
                        if application:
                            try:
                                if application.updater and application.updater.running:
                                    await application.updater.stop()
                                if application.running:
                                    await application.stop()
                                await application.shutdown()
                            except:
                                pass
                        
                        await asyncio.sleep(wait_time)
                    
                    except (TelegramError, NetworkError) as e:
                        retry_count += 1
                        wait_time = min(2 ** retry_count, 60)
                        logger.warning(f"Bot network error #{retry_count}: {e}")
                        
                        if application:
                            try:
                                if application.updater and application.updater.running:
                                    await application.updater.stop()
                                if application.running:
                                    await application.stop()
                                await application.shutdown()
                            except:
                                pass
                        
                        await asyncio.sleep(wait_time)
                    
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"Bot error #{retry_count}: {e}", exc_info=True)
                        
                        if application:
                            try:
                                if application.updater and application.updater.running:
                                    await application.updater.stop()
                                if application.running:
                                    await application.stop()
                                await application.shutdown()
                            except:
                                pass
                        
                        await asyncio.sleep(10)
                
                logger.error(f"Bot max retries ({max_retries}) exceeded")
                return True
            
            async def run_bot_forever():
                restart_count = 0
                while True:
                    should_restart = await run_bot_with_retry()
                    if not should_restart:
                        break
                    
                    restart_count += 1
                    cooldown = min(60 * restart_count, 300)
                    logger.warning(f"Bot restart #{restart_count} — cooling down {cooldown}s before retry cycle...")
                    await asyncio.sleep(cooldown)
            
            try:
                loop.run_until_complete(run_bot_forever())
            except Exception as e:
                logger.error(f"Fatal bot error: {e}", exc_info=True)
            finally:
                loop.close()
        
        except Exception as e:
            logger.error(f"Bot thread fatal error: {e}", exc_info=True)
        finally:
            global bot_initialized
            with bot_lock:
                bot_initialized = False
    
    thread = threading.Thread(target=bot_worker, daemon=True)
    thread.start()
    logger.info("Bot thread started")
    return thread


def start_cm_bot_thread():
    global cm_bot_thread, cm_bot_initialized
    
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='.env')
    
    settings = get_settings()
    token = settings.MLJCM_BOT_TOKEN or os.getenv('MLJCM_BOT_TOKEN')
    
    if not token:
        logger.info("MLJCM_BOT_TOKEN not set, Content Manager bot will not start")
        return None
        
    with cm_bot_lock:
        if cm_bot_initialized and cm_bot_thread and cm_bot_thread.is_alive():
            logger.warning("MLJCM bot already running, skipping duplicate")
            return cm_bot_thread
        cm_bot_initialized = True
        
    def cm_worker():
        try:
            from dotenv import load_dotenv
            logger.info("Initializing MLJCM bot in background thread...")
            load_dotenv(dotenv_path='.env')
            
            try:
                from content_manager.cm_bot import ContentManagerBot
                from content_manager.storage import CMStorage
            except Exception as e:
                logger.error(f"Failed to import MLJCM components: {e}", exc_info=True)
                return
                
            token = getattr(get_settings(), 'MLJCM_BOT_TOKEN', None) or os.getenv('MLJCM_BOT_TOKEN')
            if not token:
                logger.error("MLJCM_BOT_TOKEN not available in bot thread")
                return
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_cm_bot_with_retry():
                from telegram.error import Conflict, NetworkError, TelegramError
                retry_count = 0
                max_retries = 30
                
                while retry_count < max_retries:
                    cm_bot = None
                    try:
                        storage = CMStorage()
                        cm_bot = ContentManagerBot(token=token, storage=storage)
                        await cm_bot.initialize()
                        
                        try:
                            await cm_bot.application.bot.delete_webhook(drop_pending_updates=True)
                        except:
                            pass
                            
                        logger.info("Starting MLJCM polling...")
                        await cm_bot.start_polling()
                        
                        cm_stop_event = asyncio.Event()
                        
                        async def check_cm_shutdown():
                            while not is_shutting_down and cm_bot.application.updater and cm_bot.application.updater.running:
                                await asyncio.sleep(1)
                            cm_stop_event.set()
                            
                        asyncio.create_task(check_cm_shutdown())
                        await cm_stop_event.wait()
                            
                        if is_shutting_down:
                            logger.info("Shutting down MLJCM gracefully...")
                            await cm_bot.shutdown()
                            return False
                        else:
                            logger.warning("MLJCM polling stopped unexpectedly. Preparing to restart...")
                            try:
                                await cm_bot.shutdown()
                            except Exception:
                                pass
                            
                            await asyncio.sleep(10)
                            return True
                        
                    except Conflict as e:
                        retry_count += 1
                        wait_time = 30 if retry_count <= 3 else min(5 ** min(retry_count - 3, 4), 120)
                        logger.error(f"MLJCM conflict #{retry_count}: {e}")
                        
                        if cm_bot:
                            try:
                                await cm_bot.shutdown()
                            except:
                                pass
                        await asyncio.sleep(wait_time)
                        
                    except (TelegramError, NetworkError) as e:
                        retry_count += 1
                        wait_time = min(2 ** retry_count, 60)
                        logger.warning(f"MLJCM network error #{retry_count}: {e}")
                        if cm_bot:
                            try:
                                await cm_bot.shutdown()
                            except:
                                pass
                        await asyncio.sleep(wait_time)
                        
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"MLJCM Bot error #{retry_count}: {e}", exc_info=True)
                        if cm_bot:
                            try:
                                await cm_bot.shutdown()
                            except:
                                pass
                        await asyncio.sleep(10)
                        
                logger.error("MLJCM max retries exceeded")
                return True
                
            async def run_cm_bot_forever():
                restart_count = 0
                while True:
                    should_restart = await run_cm_bot_with_retry()
                    if not should_restart:
                        break
                    
                    restart_count += 1
                    cooldown = min(60 * restart_count, 300)
                    logger.warning(f"MLJCM restart #{restart_count} - sleeping {cooldown}s")
                    await asyncio.sleep(cooldown)
                    
            try:
                loop.run_until_complete(run_cm_bot_forever())
            except Exception as e:
                logger.error(f"Fatal MLJCM error: {e}", exc_info=True)
            finally:
                loop.close()
                global cm_bot_initialized
                with cm_bot_lock:
                    cm_bot_initialized = False
            
        except Exception as e:
            logger.error(f"Failed to start MLJCM bot thread: {e}", exc_info=True)
            
    cm_bot_thread = threading.Thread(target=cm_worker, daemon=True, name="MLJCM-Thread")
    cm_bot_thread.start()
    logger.info("MLJCM bot thread started")
    return cm_bot_thread



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    Handles startup and graceful shutdown.
    """
    global bot_thread, cm_bot_thread, is_shutting_down
    
    # STARTUP
    logger.info("=" * 60)
    logger.info("🚀 MLJ Results Compiler Starting")
    logger.info("=" * 60)
    
    try:
        # Validate settings
        logger.info("Validating configuration...")
        validate_settings()
        settings = get_settings()
        logger.info(f"  Environment: {settings.ENV}")
        logger.info(f"  Database: {settings.DATABASE_URL}")
        logger.info(f"  AI Enabled: {settings.ENABLE_AI_ASSISTANT}")
        logger.info(f"  Telegram Bot: {settings.ENABLE_TELEGRAM_BOT}")
        
        # Initialize database
        logger.info("Initializing database...")
        db = get_session_db()
        stats = db.get_session_statistics()
        logger.info(f"  Database initialized")
        logger.info(f"  Existing sessions: {stats['total_sessions']}")
        
        # Cleanup old sessions on startup
        logger.info("Cleaning up expired sessions...")
        cleaned = db.cleanup_expired_sessions()
        logger.info(f"  Removed {cleaned} expired sessions")
        
        # Initialize async services
        logger.info("Initializing async services...")
        await initialize_async_ai()
        await initialize_async_data_agent()
        await initialize_async_file_io()
        logger.info("✓ Async services initialized")
        
        # Start Telegram bot (if enabled)
        logger.info("Starting Telegram bot (if enabled)...")
        bot_thread = start_bot_thread()
        
        # Start MLJCM bot (if token provided)
        logger.info("Starting MLJCM bot (if token provided)...")
        cm_bot_thread = start_cm_bot_thread()
        
        # Register shutdown signal handlers
        def signal_handler(sig, frame):
            logger.warning(f"Received signal {sig}, initiating shutdown...")
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("✓ Application started successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
        raise
    
    yield  # Application is running
    
    # SHUTDOWN
    logger.info("=" * 60)
    logger.info("🛑 MLJ Results Compiler Shutting Down")
    logger.info("=" * 60)
    
    is_shutting_down = True
    
    if bot_thread and bot_thread.is_alive():
        logger.info("Waiting for bottom primary thread to stop...")
        bot_thread.join(timeout=3)
        
    if cm_bot_thread and cm_bot_thread.is_alive():
        logger.info("Waiting for cm bot thread to stop...")
        cm_bot_thread.join(timeout=3)
    
    try:
        # Cleanup async services
        logger.info("Shutting down async services...")
        await shutdown_async_ai()
        await shutdown_async_data_agent()
        await shutdown_async_file_io()
        logger.info("✓ Async services shutdown")
        
        # Cleanup
        logger.info("Closing database connections...")
        db.cleanup_expired_sessions()
        logger.info("✓ Database cleaned up")
        
        # Cleanup old files
        settings = get_settings()
        upload_dir = Path(settings.UPLOAD_DIR)
        if upload_dir.exists():
            import shutil
            for item in upload_dir.iterdir():
                if item.is_dir():
                    try:
                        shutil.rmtree(item, ignore_errors=True)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {item}: {e}")
        
        logger.info("✓ Application shut down gracefully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    settings = get_settings()
    
    # Create app with lifespan context
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Excel consolidation and grading system with Telegram bot",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["https://mljresultscompiler.onrender.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Healthcheck endpoint for monitoring and load balancers"""
        try:
            db = get_session_db()
            stats = db.get_session_statistics()
            
            # Check bot thread liveness
            bot_status = "disabled"
            if settings.ENABLE_TELEGRAM_BOT:
                if bot_thread and bot_thread.is_alive():
                    bot_status = "running"
                elif bot_initialized:
                    bot_status = "starting"
                else:
                    bot_status = "dead"
                    
            # Check CM bot thread liveness
            cm_bot_status = "disabled"
            if settings.MLJCM_BOT_TOKEN:
                if cm_bot_thread and cm_bot_thread.is_alive():
                    cm_bot_status = "running"
                elif bot_initialized: # initialized generally tracks bot boot phase
                    cm_bot_status = "starting"
                else:
                    cm_bot_status = "dead"
            
            overall = "healthy" if (bot_status in ("running", "disabled") and cm_bot_status in ("running", "disabled")) else "degraded"
            
            return {
                "status": overall,
                "version": settings.APP_VERSION,
                "environment": settings.ENV,
                "database": "ok",
                "sessions_active": stats["total_sessions"],
                "ai_enabled": settings.ENABLE_AI_ASSISTANT,
                "bot_enabled": settings.ENABLE_TELEGRAM_BOT,
                "bot_status": bot_status,
                "cm_bot_enabled": bool(settings.MLJCM_BOT_TOKEN),
                "cm_bot_status": cm_bot_status,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "version": settings.APP_VERSION,
            }, 503
    
    # Ping endpoint for keepalive
    @app.get("/ping", tags=["ping"])
    async def ping():
        """Minimal ping endpoint for keepalive systems"""
        return {"status": "pong"}
    
    # Bot health endpoint
    @app.get("/bot-health", tags=["health"])
    async def bot_health():
        """Detailed bot health check - verifies Telegram bots are alive and responsive"""
        bot_info = {
            "primary_bot": {
                "enabled": settings.ENABLE_TELEGRAM_BOT,
                "thread_alive": bot_thread is not None and bot_thread.is_alive() if bot_thread else False,
                "initialized": bot_initialized,
                "token_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            },
            "mljcm_bot": {
                "enabled": bool(settings.MLJCM_BOT_TOKEN),
                "thread_alive": cm_bot_thread is not None and cm_bot_thread.is_alive() if cm_bot_thread else False,
                "token_configured": bool(settings.MLJCM_BOT_TOKEN),
            }
        }
        
        # Determine Primary status
        if not settings.ENABLE_TELEGRAM_BOT:
            bot_info["primary_bot"]["status"] = "disabled"
        elif bot_thread and bot_thread.is_alive():
            bot_info["primary_bot"]["status"] = "healthy"
        elif bot_initialized:
            bot_info["primary_bot"]["status"] = "starting"
        else:
            bot_info["primary_bot"]["status"] = "dead"
            bot_info["primary_bot"]["action"] = "Bot thread has exited. Redeploy or restart to fix."
            
        # Determine MLJCM status
        if not settings.MLJCM_BOT_TOKEN:
            bot_info["mljcm_bot"]["status"] = "disabled"
        elif cm_bot_thread and cm_bot_thread.is_alive():
            bot_info["mljcm_bot"]["status"] = "healthy"
        elif bot_initialized:
            bot_info["mljcm_bot"]["status"] = "starting"
        else:
            bot_info["mljcm_bot"]["status"] = "dead"
            bot_info["mljcm_bot"]["action"] = "Bot thread has exited. Redeploy or restart to fix."
        
        return bot_info
    
    # Comprehensive liveness endpoint - tests ALL subsystems
    @app.get("/liveness", tags=["health"])
    async def liveness_check():
        """
        Comprehensive liveness check - verifies ALL subsystems are responsive.
        Tests: database, bot thread, async services, file system.
        Use this to confirm the entire application is functional.
        """
        from datetime import datetime
        checks = {}
        all_healthy = True
        
        # 1. Database check
        try:
            db = get_session_db()
            stats = db.get_session_statistics()
            checks["database"] = {"status": "ok", "sessions": stats["total_sessions"]}
        except Exception as e:
            checks["database"] = {"status": "error", "error": str(e)}
            all_healthy = False
        
        # 2. Bot threads check
        bot_threads = {}
        if settings.ENABLE_TELEGRAM_BOT:
            if bot_thread and bot_thread.is_alive():
                bot_threads["primary"] = {"status": "running", "thread_alive": True}
            else:
                bot_threads["primary"] = {"status": "dead", "thread_alive": False}
                all_healthy = False
        else:
            bot_threads["primary"] = {"status": "disabled"}
            
        if settings.MLJCM_BOT_TOKEN:
            if cm_bot_thread and cm_bot_thread.is_alive():
                bot_threads["mljcm"] = {"status": "running", "thread_alive": True}
            else:
                bot_threads["mljcm"] = {"status": "dead", "thread_alive": False}
                all_healthy = False
        else:
            bot_threads["mljcm"] = {"status": "disabled"}
            
        checks["telegram_bots"] = bot_threads
        
        # 3. Async AI service check
        try:
            from src.async_ai_service import get_async_ai_service
            ai_svc = get_async_ai_service()
            checks["ai_service"] = {"status": "ok", "llm_available": ai_svc.ai is not None and ai_svc.ai.llm_enabled if ai_svc.ai else False}
        except Exception as e:
            checks["ai_service"] = {"status": "error", "error": str(e)}
            # Non-critical - don't mark as unhealthy
        
        # 4. File system check
        try:
            upload_dir = Path(settings.UPLOAD_DIR)
            output_dir = Path(settings.OUTPUT_DIR)
            checks["filesystem"] = {
                "status": "ok",
                "upload_dir_exists": upload_dir.exists(),
                "output_dir_exists": output_dir.exists(),
            }
        except Exception as e:
            checks["filesystem"] = {"status": "error", "error": str(e)}
            all_healthy = False
        
        # 5. Config check
        checks["config"] = {
            "status": "ok",
            "env": settings.ENV,
            "bot_enabled": settings.ENABLE_TELEGRAM_BOT,
            "ai_enabled": settings.ENABLE_AI_ASSISTANT,
        }
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": settings.APP_VERSION,
            "checks": checks,
        }
    
    # Status endpoint
    @app.get("/status", tags=["status"])
    async def status():
        """Detailed system status"""
        db = get_session_db()
        stats = db.get_session_statistics()
        settings = get_settings()
        
        bot_status = "disabled"
        if settings.ENABLE_TELEGRAM_BOT:
            if bot_thread and bot_thread.is_alive():
                bot_status = "running"
            else:
                bot_status = "dead"
                
        cm_bot_status = "disabled"
        if settings.MLJCM_BOT_TOKEN:
            if cm_bot_thread and cm_bot_thread.is_alive():
                cm_bot_status = "running"
            else:
                cm_bot_status = "dead"
        
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENV,
            "database": {
                "url": settings.DATABASE_URL,
                "status": "ok",
            },
            "sessions": {
                "total": stats["total_sessions"],
                "completed": stats["completed_sessions"],
                "pending": stats["total_sessions"] - stats["completed_sessions"],
            },
            "operations": {
                "uploads": stats["total_uploads"],
                "consolidations": stats["total_results"],
                "transformations": stats["total_transformations"],
            },
            "features": {
                "ai_assistant": settings.ENABLE_AI_ASSISTANT,
                "telegram_bot": settings.ENABLE_TELEGRAM_BOT,
                "telegram_bot_status": bot_status,
                "cm_bot_enabled": bool(settings.MLJCM_BOT_TOKEN),
                "cm_bot_status": cm_bot_status,
            },
        }

    # Debug logs endpoint
    @app.get("/logs", tags=["debug"])
    async def get_logs(lines: int = 100):
        """Retrieve recent server logs for debugging"""
        # Read from stdout redirect or a known log file if exists.
        # Check standard destinations on render or local
        log_paths = ['server.log', 'telegram_bot.log', 'nohup.out']
        result = {}
        
        for path in log_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.readlines()
                        result[path] = "".join(content[-lines:])
                except Exception as e:
                    result[path] = f"Error reading: {e}"
        
        return {"logs": result if result else "No log files found in root directory."}
        
    # Import and register routers
    try:
        from src.web_ui_clean import router as web_ui_router
        app.include_router(web_ui_router)
        logger.info("✓ Registered web UI router")
    except Exception as e:
        logger.warning(f"Failed to load web UI router: {e}")
    
    try:
        from src.hybrid_bridge import router as hybrid_router
        app.include_router(hybrid_router, prefix="/api")
        logger.info("✓ Registered hybrid API router")
    except Exception as e:
        logger.warning(f"Failed to load hybrid router: {e}")
    
    return app


# Create global app instance for uvicorn/deployment
app = create_app()


def main():
    """Main entry point - runs the application"""
    import uvicorn
    
    settings = get_settings()
    
    # Run with Uvicorn
    uvicorn.run(
        app,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        workers=1 if settings.DEBUG else settings.WORKERS,
        reload=settings.RELOAD and settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
