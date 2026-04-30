# -*- coding: utf-8 -*-
from telegram.constants import ChatMemberStatus
from loguru import logger

async def is_user_admin(update, context) -> bool:
    """
    Checks if the user who sent the update is an admin or creator in the chat.
    In private chats, always returns True.
    """
    if not update.effective_chat or not update.effective_user:
        return False
        
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    if chat.type == chat.PRIVATE:
        return True
        
    try:
        member = await context.bot.get_chat_member(chat.id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False
