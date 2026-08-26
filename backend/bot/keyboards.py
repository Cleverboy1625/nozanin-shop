from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

DEFAULT_WEBAPP_URL = "https://nozanin-shoping.onrender.com"

def shop_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    if not webapp_url.startswith("https://") or "your-render" in webapp_url or "example.com" in webapp_url:
        webapp_url = DEFAULT_WEBAPP_URL
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=webapp_url))]
    ])
