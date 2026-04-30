# -*- coding: utf-8 -*-
from typing import Callable, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_message_markup(
    translate_func: Callable[[str], str],
    extra1: Optional[str] = None,
    is_admin: bool = False,
    blik_phone: Optional[str] = None,
):
    """Create buttons using the provided translation function"""
    rows = []

    # Row 1: Close and Shuffle (Admin only)
    if is_admin:
        rows.append(
            [
                InlineKeyboardButton("🗑️ " + translate_func("Delete event"), callback_data="DELETE_EVENT"),
                InlineKeyboardButton(
                    "🔀 " + (translate_func("Shuffle (reshuffle)") if extra1 else translate_func("Shuffle (перемешать)")),
                    callback_data="RESHUFFLE" if extra1 else "SHUFFLE",
                ),
            ]
        )

    # Row 2: Participation status (Everyone)
    rows.append(
        [
            InlineKeyboardButton("✅ " + translate_func("I am going"), callback_data="ADD"),
            InlineKeyboardButton("❌ " + translate_func("I am not going"), callback_data="REMOVE"),
            InlineKeyboardButton("🤔 " + translate_func("Thinking"), callback_data="THINK"),
        ]
    )

    # Row 3: Legioneers (Everyone)
    rows.append(
        [
            InlineKeyboardButton(translate_func("Plus +"), callback_data="ADD_LEGIONEER"),
            InlineKeyboardButton(translate_func("Minus -"), callback_data="REMOVE_LEGIONEER"),
            InlineKeyboardButton(translate_func("- All"), callback_data="REMOVE_ALL_LEGIONEERS"),
        ]
    )

    # Row 4: Payment (Everyone) - Only if BLIK phone is attached
    if blik_phone:
        rows.append([InlineKeyboardButton(translate_func("💰 Payment confirmed"), callback_data="PAY")])

    if is_admin:
        # Row 5: Admin actions
        rows.append(
            [
                InlineKeyboardButton("🟨 " + translate_func("Penalty"), callback_data="PENALTY_MENU"),
            ]
        )

        # Row 6: Team count (Admin only)
        if extra1:
            rows.append(
                [
                    InlineKeyboardButton(translate_func("Team count (+1)"), callback_data="INC_TEAMS"),
                    InlineKeyboardButton(translate_func("Team count (-1)"), callback_data="DEC_TEAMS"),
                ]
            )

        # Row 6: Limit (Admin only)
        rows.append(
            [
                InlineKeyboardButton(translate_func("Limit") + ":", callback_data="IGNORE"),
                InlineKeyboardButton("14", callback_data="SET_LIMIT_14"),
                InlineKeyboardButton("16", callback_data="SET_LIMIT_16"),
                InlineKeyboardButton("18", callback_data="SET_LIMIT_18"),
                InlineKeyboardButton("21", callback_data="SET_LIMIT_21"),
            ]
        )

    return InlineKeyboardMarkup(rows)


def build_confirmation_markup(translate_func: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Create confirmation buttons for event deletion"""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ " + translate_func("Yes, delete"), callback_data="CONFIRM_DELETE_EVENT"),
                InlineKeyboardButton("❌ " + translate_func("Cancel"), callback_data="CANCEL_DELETE_EVENT"),
            ]
        ]
    )


def _serialize_inline_kb(kb: InlineKeyboardMarkup) -> str:
    if not kb or not kb.inline_keyboard:
        return ""
    rows = []
    for row in kb.inline_keyboard:
        rows.append("|".join(f"{btn.text}::{btn.callback_data or btn.url or ''}" for btn in row))
    return "\n".join(rows)


def build_penalty_selection_markup(players: list, translate_func: Callable[[str], str], action_prefix: str, extra_arg: str = ""):
    """
    Create a list of buttons for selecting a player for an action (PENALTY or PENALTY_REMOVE)
    action_prefix: e.g. "PENALTY" or "PEN_REM"
    extra_arg: e.g. "14" (days) for penalty
    """
    rows = []
    for uid, name in players:
        cb_data = f"{action_prefix}_{uid}"
        if extra_arg:
            cb_data += f"_{extra_arg}"
        rows.append([InlineKeyboardButton(name, callback_data=cb_data)])
    return InlineKeyboardMarkup(rows)


def build_penalty_markup(players: list, translate_func: Callable[[str], str], days: int = 14):
    """Backward compatibility for penalty markup"""
    return build_penalty_selection_markup(players, translate_func, "PENALTY", str(days))

def build_penalty_duration_markup(uid: int, translate_func: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Create buttons for selecting penalty duration"""
    options = [
        (1, translate_func("1 day")),
        (3, translate_func("3 days")),
        (7, translate_func("7 days")),
        (14, translate_func("14 days")),
        (30, translate_func("30 days")),
    ]
    rows = []
    # 2 buttons per row
    for i in range(0, len(options), 2):
        row = []
        for days, label in options[i:i+2]:
            row.append(InlineKeyboardButton(label, callback_data=f"PEN_DUR_{uid}_{days}"))
        rows.append(row)
    
    return InlineKeyboardMarkup(rows)


def build_penalty_main_menu_markup(translate_func: Callable[[str], str]):
    rows = [
        [
            InlineKeyboardButton("➕ " + translate_func("Add penalty"), callback_data="PENALTY_ADD_FLOW"),
            InlineKeyboardButton("➖ " + translate_func("Remove penalty"), callback_data="PENALTY_REMOVE_FLOW"),
        ],
        [InlineKeyboardButton("⬅️ " + translate_func("Back"), callback_data="SHOW_INFO")]
    ]
    return InlineKeyboardMarkup(rows)
