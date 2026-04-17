# -*- coding: utf-8 -*-
from typing import Optional, Callable
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_message_markup(translate_func: Callable[[str], str], extra1: Optional[str] = None):
    """Create buttons using the provided translation function"""
    rows = [
        # Row 1: Close and Shuffle
        [
            InlineKeyboardButton("🧒 " + translate_func('Close collection'), callback_data='CLOSE_EVENT'),
            InlineKeyboardButton("🔀 " + (translate_func('Shuffle (reshuffle)') if extra1 else translate_func('Shuffle (перемешать)')), 
                                  callback_data='RESHUFFLE' if extra1 else 'SHUFFLE')
        ],
        # Row 2: Participation status
        [
            InlineKeyboardButton("✅ " + translate_func('I am going'), callback_data='ADD'),
            InlineKeyboardButton("❌ " + translate_func('I am not going'), callback_data='REMOVE'),
            InlineKeyboardButton("🤔 " + translate_func('Thinking'), callback_data='THINK')
        ],
        # Row 3: Legioneers
        [
            InlineKeyboardButton(translate_func('Plus +'), callback_data='ADD_LEGIONEER'),
            InlineKeyboardButton(translate_func('Minus -'), callback_data='REMOVE_LEGIONEER'),
            InlineKeyboardButton(translate_func('- All'), callback_data='REMOVE_ALL_LEGIONEERS')
        ],
        # Row 4: Payment
        [
            InlineKeyboardButton(translate_func('💰 Payment confirmed'), callback_data='PAY')
        ]
    ]
    
    if extra1:
        rows.append([
            InlineKeyboardButton(translate_func('Team count (+1)'), callback_data='INC_TEAMS'),
            InlineKeyboardButton(translate_func('Team count (-1)'), callback_data='DEC_TEAMS')
        ])
        
    rows.append([
        InlineKeyboardButton(translate_func('Limit') + ":", callback_data='IGNORE'),
        InlineKeyboardButton('14', callback_data='SET_LIMIT_14'),
        InlineKeyboardButton('16', callback_data='SET_LIMIT_16'),
        InlineKeyboardButton('18', callback_data='SET_LIMIT_18'),
        InlineKeyboardButton('21', callback_data='SET_LIMIT_21')
    ])
        
    return InlineKeyboardMarkup(rows)

def _serialize_inline_kb(kb: InlineKeyboardMarkup) -> str:
    if not kb or not kb.inline_keyboard: return ""
    rows = []
    for row in kb.inline_keyboard:
        rows.append("|".join(f"{btn.text}::{btn.callback_data or btn.url or ''}" for btn in row))
    return "\n".join(rows)
