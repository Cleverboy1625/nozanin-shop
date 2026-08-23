from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


def shop_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=webapp_url))]
    ])
