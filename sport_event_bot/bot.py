# -*- coding: utf-8 -*-
import asyncio
import os
import signal
import sys
import warnings

from dotenv import load_dotenv
from loguru import logger
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from telegram.warnings import PTBUserWarning

# Load environment
load_dotenv(".env.development")
load_dotenv()

# Fix imports to support both direct run and module run
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Support package/standalone imports
try:
    from sport_event_bot import db_postgres as db
    from sport_event_bot.handlers import admin, callback, common, event, event_conv, event_mgmt, msg_updates, player
except (ImportError, ValueError):
    try:
        import db_postgres as db
        from handlers import admin, callback, common, event, event_conv, event_mgmt, msg_updates, player
    except ImportError:
        # Fallback when running as module but absolute imports fail
        from . import db_postgres as db
        from .handlers import admin, callback, common, event, event_conv, event_mgmt, msg_updates, player


BOT_DIR = os.path.dirname(os.path.abspath(__file__))


async def health_check_handler(reader, writer):
    """Simple HTTP health-check responder"""
    await reader.read(100)
    response = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
    writer.write(response.encode())
    await writer.drain()
    writer.close()


async def shutdown(application, health_server=None):
    logger.info("Shutting down bot...")
    if health_server:
        health_server.close()
        await health_server.wait_closed()
        logger.info("Health server closed")

    # Stop updater if it's running
    if application.updater and application.updater.running:
        await application.updater.stop()

    if application.running:
        await application.stop()

    # application.shutdown() is safe to call as it checks internally if initialized
    await application.shutdown()
    logger.info("Bot shutdown complete")


async def ping_php_server():
    """Background task to ping the PHP server to keep it awake"""
    import httpx
    
    pay_url = os.getenv("PAYMENTS_PAGE_URL")
    if not pay_url:
        logger.warning("No PAYMENTS_PAGE_URL set, skipping PHP server ping.")
        return
        
    logger.info(f"Starting background ping task for {pay_url}")
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await asyncio.sleep(60) # Ping every 60 seconds
                response = await client.get(pay_url, timeout=10.0)
                logger.debug(f"Pinged PHP server: {response.status_code}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Failed to ping PHP server: {e}")


async def main():
    warnings.filterwarnings("ignore", category=PTBUserWarning, message=".*per_message=False.*")
    logger.remove()
    logger.add(os.path.join(BOT_DIR, "logs", "logs.log"), level="INFO")
    logger.add(sys.stderr, level="WARNING")

    api_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not api_token:
        try:
            with open(os.path.join(BOT_DIR, "token.txt"), encoding="utf-8") as f:
                api_token = f.readline().strip()
        except Exception:
            pass
    if not api_token:
        sys.exit("No bot token found")

    proxy_url = os.getenv("TELEGRAM_PROXY")
    # Use custom timeouts to mitigate httpx.ReadError
    request = HTTPXRequest(connect_timeout=15, read_timeout=20)
    builder = Application.builder().token(api_token).request(request)
    if proxy_url:
        builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)
    application = builder.build()

    db.init_database()
    port = int(os.getenv("PORT", "10000"))
    health_server = None
    try:
        health_server = await asyncio.start_server(health_check_handler, "0.0.0.0", port)
        asyncio.create_task(health_server.serve_forever())
    except Exception as e:
        logger.warning(f"Failed to start health server: {e}")

    # Handlers
    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(CommandHandler("help", common.show_help))
    application.add_handler(CommandHandler("lang", common.set_language))

    application.add_handler(CommandHandler("add", player.add_player))
    application.add_handler(CommandHandler("remove", player.remove_player))
    application.add_handler(CommandHandler("add_leg", player.add_leg))
    application.add_handler(CommandHandler("rem_leg", player.rem_leg))
    application.add_handler(CommandHandler("pay", player.confirm_payment))

    application.add_handler(CommandHandler("info", event_mgmt.show_info))
    application.add_handler(CommandHandler("limit", admin.set_players_limit))
    application.add_handler(CommandHandler("stat", admin.show_stat))
    application.add_handler(CommandHandler("penalty", admin.penalty_player))
    application.add_handler(CommandHandler("payments", admin.show_payments))
    application.add_handler(CommandHandler("fix", admin.fix_ui))
    application.add_handler(CommandHandler("set_lists_topic", admin.set_lists_topic))
    application.add_handler(CommandHandler("set_logs_topic", admin.set_logs_topic))

    application.add_handler(CommandHandler("event_remove", event.remove_all_chat_events))
    application.add_handler(CommandHandler("event_update", event.update_event))
    application.add_handler(CommandHandler("event_datetime", event.set_event_datetime))
    application.add_handler(CommandHandler("blik", event.set_blik))

    # Conversation
    event_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("event", event_conv.create_new_event)],
        states={
            event_conv.EVENT_SET_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_conv.event_name_handler),
                CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_NAME|CHG_NAME)$"),
            ],
            event_conv.EVENT_SET_LIMIT: [
                CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_LIMIT|CHG_LIMIT|EV_LIMIT_.*)$")
            ],
            event_conv.EVENT_SET_DATETIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_conv.event_datetime_handler),
                CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_DT|CHG_DT|CONF_DEFAULT_DT)$"),
            ],
            event_conv.EVENT_SET_PAYMENT: [
                CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_PAY|CHG_PAY|PAY_FREE|PAY_PAID)$")
            ],
            event_conv.EVENT_SET_BLIK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_conv.event_blik_handler),
                CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_BLIK|CHG_BLIK)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", event_conv.event_cancel)],
        allow_reentry=True,
        per_message=False,
    )
    application.add_handler(event_conv_handler)
    application.add_handler(CallbackQueryHandler(callback.button))
    application.add_handler(
        MessageHandler(filters.StatusUpdate.FORUM_TOPIC_CREATED, msg_updates.forum_topic_created_handler)
    )
    application.add_handler(
        MessageHandler(filters.TEXT | filters.StatusUpdate.NEW_CHAT_MEMBERS, msg_updates.unknown_command_handler)
    )

    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

        # Start background ping task
        ping_task = asyncio.create_task(ping_php_server())

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        def sig_handler():
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, sig_handler)
            except NotImplementedError:
                pass

        await stop_event.wait()
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        raise
    finally:
        await shutdown(application, health_server)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
