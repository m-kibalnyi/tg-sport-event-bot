# -*- coding: utf-8 -*-
import sys
import os
import signal
import asyncio
import warnings
from loguru import logger
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from telegram.warnings import PTBUserWarning
from dotenv import load_dotenv

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
    from sport_event_bot import common, event_conv, event_mgmt, player, admin, callback, msg_updates, event
except (ImportError, ValueError):
    import db_postgres as db
    from handlers import common, event_conv, event_mgmt, player, admin, callback, msg_updates, event


BOT_DIR = os.path.dirname(os.path.abspath(__file__))

async def health_check_handler(reader, writer):
    """Simple HTTP health-check responder"""
    data = await reader.read(100)
    response = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
    writer.write(response.encode())
    await writer.drain()
    writer.close()

async def shutdown(application, loop):
    logger.info("Shutting down bot...")
    await application.stop()
    await application.shutdown()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks: task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    warnings.filterwarnings("ignore", category=PTBUserWarning, message=".*per_message=False.*")
    logger.remove()
    logger.add(os.path.join(BOT_DIR, "logs", "logs.log"), level="INFO")
    logger.add(sys.stderr, level="WARNING")

    api_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not api_token:
        try:
            with open(os.path.join(BOT_DIR, 'token.txt'), encoding='utf-8') as f:
                api_token = f.readline().strip()
        except: pass
    if not api_token: sys.exit("No bot token found")

    proxy_url = os.getenv('TELEGRAM_PROXY')
    builder = Application.builder().token(api_token)
    if proxy_url: builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)
    application = builder.build()

    db.init_database()
    port = int(os.getenv("PORT", "10000"))
    try:
        health_server = await asyncio.start_server(health_check_handler, '0.0.0.0', port)
        asyncio.create_task(health_server.serve_forever())
    except: pass

    # Handlers
    application.add_handler(CommandHandler('start', common.start))
    application.add_handler(CommandHandler('help', common.show_help))
    application.add_handler(CommandHandler('lang', common.set_language))
    
    application.add_handler(CommandHandler('add', player.add_player))
    application.add_handler(CommandHandler('remove', player.remove_player))
    application.add_handler(CommandHandler('add_leg', player.add_leg))
    application.add_handler(CommandHandler('rem_leg', player.rem_leg))
    application.add_handler(CommandHandler('pay', player.confirm_payment))
    
    application.add_handler(CommandHandler('info', event_mgmt.show_info))
    application.add_handler(CommandHandler('limit', admin.set_players_limit))
    application.add_handler(CommandHandler('stat', admin.show_stat))
    application.add_handler(CommandHandler('penalty', admin.penalty_player))
    application.add_handler(CommandHandler('payments', admin.show_payments))
    application.add_handler(CommandHandler('fix', admin.fix_ui))
    application.add_handler(CommandHandler('set_lists_topic', admin.set_lists_topic))
    application.add_handler(CommandHandler('set_logs_topic', admin.set_logs_topic))

    application.add_handler(CommandHandler('event_remove', event.remove_all_chat_events))
    application.add_handler(CommandHandler('event_update', event.update_event))
    application.add_handler(CommandHandler('event_datetime', event.set_event_datetime))
    application.add_handler(CommandHandler('blik', event.set_blik))

    # Conversation
    event_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('event', event_conv.create_new_event)],
        states={
            event_conv.EVENT_SET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_conv.event_name_handler), CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_NAME|CHG_NAME)$")],
            event_conv.EVENT_SET_LIMIT: [CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_LIMIT|CHG_LIMIT|EV_LIMIT_.*)$")],
            event_conv.EVENT_SET_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_conv.event_datetime_handler), CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_DT|CHG_DT|CONF_DEFAULT_DT)$")],
            event_conv.EVENT_SET_PAYMENT: [CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_PAY|CHG_PAY|PAY_FREE|PAY_PAID)$")],
            event_conv.EVENT_SET_BLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_conv.event_blik_handler), CallbackQueryHandler(event_conv.event_callback, pattern="^(CONF_BLIK|CHG_BLIK)$")],
        },
        fallbacks=[CommandHandler('cancel', event_conv.event_cancel)],
        allow_reentry=True, per_message=False
    )
    application.add_handler(event_conv_handler)
    application.add_handler(CallbackQueryHandler(callback.button))
    application.add_handler(MessageHandler(filters.StatusUpdate.FORUM_TOPIC_CREATED, msg_updates.forum_topic_created_handler))
    application.add_handler(MessageHandler(filters.TEXT | filters.StatusUpdate.NEW_CHAT_MEMBERS, msg_updates.unknown_command_handler))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    def sig_handler(): stop_event.set()
    for sig in (signal.SIGINT, signal.SIGTERM): loop.add_signal_handler(sig, sig_handler)
    await stop_event.wait()
    await shutdown(application, loop)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(main())
    except KeyboardInterrupt: pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()