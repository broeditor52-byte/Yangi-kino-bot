import asyncio
import logging
import os
from datetime import datetime, timedelta
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# ==========================================
#               SOZLAMALAR
# ==========================================
BOT_TOKEN = "8626387450:AAEcwHBWlfYDhJ3eIL43DqMJBDU0xeo8irc"
ADMIN_ID = 7537910482 , 8631477823
CARD_NUMBER = "9860 1666 5645 6349"
CARD_OWNER = "AZIZBEK K"

# FAQAT SHU KANAL TEKSHIRILADI:
MAIN_CHANNEL = "@yangikinoobott"

# TUGMADA KO'RINADIGAN ZAYAVKA KANALLAR (Bot bularni TEKSHIRMAYDI, shunchaki tugma):
CHANNELS_TO_SHOW = [
    {"name": "📢 1 - Zayavka Kanal", "url": "https://t.me/+US3wQJVDWA1mMjQy"},
    {"name": "📢 2 - Zayavka Kanal", "url": "https://t.me/+UgzA_Y73q8Y4Y2Uy"},
    {"name": "⭐️ Asosiy Kanal", "url": f"https://t.me/{MAIN_CHANNEL[1:]}"}
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
#        CALLBACK DATA FABRIKALARI
# ==========================================
class TariffCB(CallbackData, prefix="tariff"):
    days: int
    price: int

class ApproveCB(CallbackData, prefix="approve"):
    user_id: int
    days: int

class RejectCB(CallbackData, prefix="reject"):
    user_id: int

# ==========================================
#        MA'LUMOTLAR BAZASI (SQLITE)
# ==========================================
async def init_db():
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                premium_until DATETIME
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code INTEGER PRIMARY KEY,
                file_id TEXT
            )
        """)
        await db.commit()

async def add_user(user_id):
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def is_premium(user_id) -> bool:
    async with aiosqlite.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row and row[0]:
            premium_until = datetime.fromisoformat(row[0])
            return datetime.now() < premium_until
        return False

# ==========================================
#      MAJBURIY OBUNA (FAQAT @azizakabott)
# ==========================================
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        if member.status in ['left', 'kicked']:
            return False
        return True
    except Exception:
        return False

def get_sub_keyboard():
    builder = []
    for ch in CHANNELS_TO_SHOW:
        builder.append([InlineKeyboardButton(text=ch["name"], url=ch["url"])])
    
    builder.append([InlineKeyboardButton(text="⚡️ TEKSHIRISH ⚡️", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

main_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 PREMIUM VIP 💎")]
    ],
    resize_keyboard=True
)

# ==========================================
#              KLAVIATURALAR
# ==========================================
def get_tariffs_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ 1 KUNLIK OBUNA — 5 000 SO'M ⚡️", callback_data=TariffCB(days=1, price=5000).pack())],
        [InlineKeyboardButton(text="🔥 1 HAFTALIK OBUNA — 10 000 SO'M 🔥", callback_data=TariffCB(days=7, price=10000).pack())],
        [InlineKeyboardButton(text="👑 1 OYLIK OBUNA — 20 000 SO'M 👑", callback_data=TariffCB(days=30, price=20000).pack())],
        [InlineKeyboardButton(text="◀️ ORQAGA ◀️", callback_data="back_to_start")]
    ])

# ==========================================
#              FSM STATE'LAR
# ==========================================
class AdminState(StatesGroup):
    waiting_for_broadcast = State()

class PaymentState(StatesGroup):
    waiting_for_receipt = State()

# ==========================================
#       FOYDALANUVCHI HANDLERLARI
# ==========================================
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await add_user(message.from_user.id)
    subscribed = await check_subscription(message.from_user.id)
    
    if subscribed:
        await message.answer(
            f"👋 <b>Assalomu alaykum</b> <b>{message.from_user.first_name}</b>, <b>botimizga xush kelibsiz!</b> 🎉\n\n"
            f"✍️ <b>Kino kodini yuboring...</b> 🎬", 
            reply_markup=main_reply_keyboard, 
            parse_mode="HTML"
        )
    else:
        text = (
            "⚠️ <b>Kechirasiz, botimizdan foydalanish uchun ushbu kanallarga obuna bo'lishingiz/zayavka yuborishingiz kerak!</b> 📌\n\n"
            "💎 <b>Premium obuna sotib olib, kanallarga obuna bo'lmasdan foydalanishingiz ham mumkin.</b> 🚀"
        )
        await message.answer(text, reply_markup=get_sub_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "check_sub")
async def check_sub_handler(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await call.message.answer(
            "✅ <b>Obuna muvaffaqiyatli tasdiqlandi!</b> 🎉\n\n✍️ <b>Kino kodini yuboring...</b> 🎬", 
            reply_markup=main_reply_keyboard, 
            parse_mode="HTML"
        )
    else:
        await call.answer("❌ Kanallarga obuna bo'lmadingiz!", show_alert=True)

@dp.callback_query(F.data == "back_to_start")
async def back_to_start_handler(call: types.CallbackQuery):
    await call.message.delete()
    fake_msg = types.Message(
        message_id=call.message.message_id,
        date=call.message.date,
        chat=call.message.chat,
        from_user=call.from_user
    )
    await start_handler(fake_msg)

@dp.message(F.text.contains("PREMIUM VIP") | (F.text == "💎 Premium"))
async def premium_text_handler(message: types.Message):
    text = (
        "💎 <b>PREMIUM OBUNA</b> 👑\n\n"
        "✨ <b>Premium orqali quyidagilarga ega bo'lasiz:</b>\n"
        "🟢 <b>Kanallarga obuna bo'lmasdan kino ko'rish</b>\n"
        "🟢 <b>Reklamalarsiz tezkor foydalanish</b>\n"
        "🟢 <b>Yuqori sifatdagi kinolarni tomosha qilish</b>\n\n"
        "📋 <b>Quyidagi tariflardan birini tanlang:</b> ⬇️"
    )
    await message.answer(text, reply_markup=get_tariffs_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "premium_menu")
async def premium_menu_handler(call: types.CallbackQuery):
    text = (
        "💎 <b>PREMIUM OBUNA</b> 👑\n\n"
        "✨ <b>Premium orqali quyidagilarga ega bo'lasiz:</b>\n"
        "🟢 <b>Kanallarga obuna bo'lmasdan kino ko'rish</b>\n"
        "🟢 <b>Reklamalarsiz tezkor foydalanish</b>\n"
        "🟢 <b>Yuqori sifatdagi kinolarni tomosha qilish</b>\n\n"
        "📋 <b>Quyidagi tariflardan birini tanlang:</b> ⬇️"
    )
    try:
        await call.message.edit_text(text, reply_markup=get_tariffs_keyboard(), parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=get_tariffs_keyboard(), parse_mode="HTML")
      @dp.callback_query(TariffCB.filter())
async def tariff_selected_handler(call: types.CallbackQuery, callback_data: TariffCB, state: FSMContext):
    await state.update_data(days=callback_data.days, price=callback_data.price)
    
    text = (
        "💳 <b>PREMIUM OBUNA — TO'LOV MA'LUMOTLARI</b> 💸\n\n"
        f"📦 <b>Tarif:</b> <b>{callback_data.days} kunlik obuna</b>\n"
        f"💳 <b>Karta raqami:</b> <code>{CARD_NUMBER}</code>\n"
        f"👤 <b>Karta egasi:</b> <b>{CARD_OWNER}</b>\n"
        f"💰 <b>To'lov summasi:</b> <b>{callback_data.price:,} so'm</b>\n\n"
        "⚠️ <b>Diqqat:</b>\n"
        "📸 <b>Pulni o'tkazgandan so'ng, chekni (skrinshotni) yuborish uchun pastdagi tugmani bosing!</b> ⬇️"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 CHEK RASMINI YUBORISH 📤", callback_data="send_receipt")],
        [InlineKeyboardButton(text="◀️ ORQAGA ◀️", callback_data="premium_menu")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "send_receipt")
async def ask_receipt_handler(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_receipt)
    await call.message.answer("📸 <b>Iltimos, to'lovni tasdiqlovchi chek (skrinshot) rasmini shu yerga yuboring:</b>", parse_mode="HTML")
    await call.answer()

@dp.message(PaymentState.waiting_for_receipt, F.photo)
async def receipt_received_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    days = data.get("days", 30)
    price = data.get("price", 0)
    photo_file_id = message.photo[-1].file_id
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=ApproveCB(user_id=message.from_user.id, days=days).pack()),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=RejectCB(user_id=message.from_user.id).pack())
        ]
    ])
    
    caption = (
        "💳 <b>YANGI TO'LOV CHEKI KELDI!</b> 🚨\n\n"
        f"👤 <b>Foydalanuvchi:</b> <b>{message.from_user.full_name}</b>\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"📦 <b>Tarif:</b> <b>{days} kunlik</b>\n"
        f"💰 <b>Summa:</b> <b>{price:,} so'm</b>"
    )
    
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=caption, reply_markup=admin_kb, parse_mode="HTML")
    await message.answer("✅ <b>Chekingiz adminga yuborildi!</b> ⏳\n<b>Adminlar tekshirib chiqquncha kuting.</b>", parse_mode="HTML", reply_markup=main_reply_keyboard)
    await state.clear()

@dp.callback_query(ApproveCB.filter(), F.from_user.id == ADMIN_ID)
async def approve_payment_handler(call: types.CallbackQuery, callback_data: ApproveCB):
    user_id = callback_data.user_id
    days = callback_data.days
    
    now = datetime.now()
    async with aiosqlite.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        
        if row and row[0]:
            current_expiry = datetime.fromisoformat(row[0])
            if current_expiry > now:
                new_expiry = current_expiry + timedelta(days=days)
            else:
                new_expiry = now + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)
        
        await db.execute("UPDATE users SET premium_until = ? WHERE user_id = ?", (new_expiry.isoformat(), user_id))
        await db.commit()
        
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 <b>Tabriklaymiz! To'lovingiz tasdiqlandi.</b> 👑\n<b>Sizga {days} kunlik Premium obuna berildi. Endi kino kodlarini yuborishingiz mumkin!</b> 🎬",
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    await call.message.edit_caption(caption=call.message.caption + "\n\n✅ <b>TASDIQLANDI</b>", parse_mode="HTML")
    await call.answer("To'lov tasdiqlandi!", show_alert=True)

@dp.callback_query(RejectCB.filter(), F.from_user.id == ADMIN_ID)
async def reject_payment_handler(call: types.CallbackQuery, callback_data: RejectCB):
    user_id = callback_data.user_id
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ <b>Kechirasiz, to'lov chekingiz rad etildi.</b> ⚠️\n<b>Iltimos, to'g'ri chek yuborganingizga ishonch hosil qiling.</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    await call.message.edit_caption(caption=call.message.caption + "\n\n❌ <b>RAD ETILDI</b>", parse_mode="HTML")
    await call.answer("To'lov rad etildi.", show_alert=True)

# ==========================================
#     ADMIN: /prem, /unprem va /backup
# ==========================================
@dp.message(Command("prem"), F.from_user.id == ADMIN_ID)
async def admin_set_premium(message: types.Message):
    args = message.text.split()
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        await message.reply("❌ <b>Xato format!</b>\n\n<b>Ishlatilishi:</b> <code>/prem user_id kun</code>\n<b>Misol:</b> <code>/prem 123456789 30</code>", parse_mode="HTML")
        return
    
    uid = int(args[1])
    days = int(args[2])
    now = datetime.now()
    
    async with aiosqlite.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT premium_until FROM users WHERE user_id = ?", (uid,))
        row = await cursor.fetchone()
        
        if row and row[0]:
            current_expiry = datetime.fromisoformat(row[0])
            if current_expiry > now:
                new_expiry = current_expiry + timedelta(days=days)
            else:
                new_expiry = now + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)
            await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
            
        await db.execute("UPDATE users SET premium_until = ? WHERE user_id = ?", (new_expiry.isoformat(), uid))
        await db.commit()
    
    await message.reply(f"✅ <b>{uid}</b> <b>ID raqamli foydalanuvchiga</b> <b>{days} kunlik Premium berildi!</b> 👑", parse_mode="HTML")
    try:
        await bot.send_message(uid, f"🎉 <b>Sizga admin tomonidan {days} kunlik Premium obuna taqdim etildi!</b> ✨", parse_mode="HTML")
    except:
        pass

@dp.message(Command("unprem"), F.from_user.id == ADMIN_ID)
async def admin_remove_premium(message: types.Message):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.reply("❌ <b>Xato format!</b>\n\n<b>Ishlatilishi:</b> <code>/unprem user_id</code>\n<b>Misol:</b> <code>/unprem 123456789</code>", parse_mode="HTML")
        return
    
    uid = int(args[1])
    
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET premium_until = NULL WHERE user_id = ?", (uid,))
        await db.commit()
    
    await message.reply(f"✅ <b>{uid}</b> <b>ID raqamli foydalanuvchidan Premium olib tashlandi!</b>", parse_mode="HTML")
    try:
        await bot.send_message(uid, "⚠️ <b>Sizning Premium obunangiz admin tomonidan bekor qilindi.</b>", parse_mode="HTML")
    except:
        pass

@dp.message(Command("backup"), F.from_user.id == ADMIN_ID)
async def backup_database(message: types.Message):
    if os.path.exists("bot_database.db"):
        await message.answer_document(
            types.FSInputFile("bot_database.db"),
            caption="📂 <b>Bazaning nusxasi (Backup) tayyor!</b> 💾\n\n<b>Barcha ma'lumotlar xavfsiz saqlangan.</b>",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ <b>Hozircha baza fayli topilmadi.</b>", parse_mode="HTML")

@dp.message(F.document & (F.from_user.id == ADMIN_ID))
async def restore_database(message: types.Message):
    if message.document.file_name.endswith(".db"):
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        await bot.download(file, destination="bot_database.db")
        await message.reply("✅ <b>Baza muvaffaqiyatli tiklandi!</b> 💾", parse_mode="HTML")
      # Kino qidirish
@dp.message(F.text.regexp(r'^\d+$'))
async def find_movie_handler(message: types.Message):
    movie_code = int(message.text)
    
    async with aiosqlite.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT file_id FROM movies WHERE code = ?", (movie_code,))
        row = await cursor.fetchone()
        
    if not row:
        await message.reply("❌ <b>Kino kodini noto'g'ri yubordingiz!</b> ⚠️", parse_mode="HTML")
        return

    if not await is_premium(message.from_user.id) and message.from_user.id != ADMIN_ID:
        text = (
            "🔒 <b>Ushbu kino faqat «Premium» foydalanuvchilar uchun!</b> 👑\n\n"
            "❗️ <b>Premium obunaga ega bo'ling.</b> 🚀"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 PREMIUM OLISH 💎", callback_data="premium_menu")]
        ])
        await message.reply(text, reply_markup=kb, parse_mode="HTML")
        return

    bot_info = await bot.get_me()
    await message.reply_video(video=row[0], caption=f"🎬 <b>Kino kodi:</b> <b>{movie_code}</b>\n\n🤖 <b>@{bot_info.username}</b>", parse_mode="HTML")

# ==========================================
#               ADMIN PANEL
# ==========================================
@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add_movie_handler(message: types.Message):
    if not message.caption or not message.caption.isdigit():
        await message.reply("❌ <b>Kino qo'shish uchun video bilan birga uning kodini (faqat raqam) yozib yuboring!</b>", parse_mode="HTML")
        return
    
    movie_code = int(message.caption)
    file_id = message.video.file_id
    
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("INSERT OR REPLACE INTO movies (code, file_id) VALUES (?, ?)", (movie_code, file_id))
        await db.commit()
        
    await message.reply(f"✅ <b>Kino bazaga qo'shildi!</b> 🎬\n<b>Kodi:</b> <b>{movie_code}</b>", parse_mode="HTML")

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel_handler(message: types.Message):
    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="admin_broadcast")]
    ])
    await message.answer("👨‍💻 <b>Admin panelga xush kelibsiz!</b> ⚙️\n\n<b>Quyidagi menyudan kerakli bo'limni tanlang:</b>", reply_markup=btn, parse_mode="HTML")

@dp.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def admin_stats_handler(call: types.CallbackQuery):
    async with aiosqlite.connect("bot_database.db") as db:
        users_count = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        movies_count = await (await db.execute("SELECT COUNT(*) FROM movies")).fetchone()
    
    text = (
        "📊 <b>Statistika</b>\n"
        f"• Obunachilar soni: {users_count[0]:,} ta\n"
        "• Faol obunachilar: 0 ta\n"
        "• Tark etganlar: 0 ta\n\n"
        "📈 <b>Obunachilar qo'shilishi</b>\n"
        "• Oxirgi 24 soat: +0 obunachi\n"
        "• Oxirgi 7 kun: +0 obunachi\n"
        "• Oxirgi 30 kun: +0 obunachi\n\n"
        "📊 <b>Faollik</b>\n"
        "• Oxirgi 24 soatda faol: 0 ta\n"
        "• Oxirgi 7 kun faol: 0 ta\n"
        "• Oxirgi 30 kun faol: 0 ta\n\n"
        "📥 <b>Yuklanishlar</b>\n"
        "• Oxirgi 24 soat: 0 ta\n"
        "• Oxirgi 7 kun: 0 ta\n"
        "• Oxirgi 30 kun: 0 ta\n\n"
        f"🎬 <b>Kinolar soni:</b> {movies_count[0]} ta"
    ).replace(",", " ")
    
    back_btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")]])
    await call.message.edit_text(text, reply_markup=back_btn, parse_mode="HTML")

@dp.callback_query(F.data == "admin_back", F.from_user.id == ADMIN_ID)
async def admin_back_handler(call: types.CallbackQuery):
    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="admin_broadcast")]
    ])
    await call.message.edit_text("👨‍💻 <b>Admin panelga xush kelibsiz!</b> ⚙️\n\n<b>Quyidagi menyudan kerakli bo'limni tanlang:</b>", reply_markup=btn, parse_mode="HTML")

@dp.callback_query(F.data == "admin_broadcast", F.from_user.id == ADMIN_ID)
async def admin_broadcast_handler(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer(
        "📢 <b>Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:</b>\n"
        "<i>(Matn, rasm yoki video yuborishingiz mumkin)</i>\n\n"
        "<b>Bekor qilish uchun /cancel buyrug'ini yuboring.</b>", 
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
async def send_broadcast_handler(message: types.Message, state: FSMContext):
    if message.text == '/cancel':
        await message.answer("❌ <b>Xabar tarqatish bekor qilindi.</b>", parse_mode="HTML")
        await state.clear()
        return

    await message.answer("⏳ <b>Xabar tarqatish boshlandi...</b>", parse_mode="HTML")
    
    async with aiosqlite.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()
        
    count = 0
    for user in users:
        try:
            await message.copy_to(chat_id=user[0])
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(f"✅ <b>Xabar {count} ta foydalanuvchiga muvaffaqiyatli yuborildi!</b> 🎉", parse_mode="HTML")
    await state.clear()

# ==========================================
#               MAIN
# ==========================================
async def handle_ping(request):
    return web.Response(text="Bot ishlamoqda!")

async def main():
    await init_db()
    
    # Eski webhooklarni va navbatda turgan xabarlarni tozalaymiz
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Render ajratgan PORT ni olish va HTTP server yaratish
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # aiogram polling ni boshlash
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
