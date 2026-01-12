import json, qrcode, random, string
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8546034730:AAEIEE11iW2tsOhIydjQ0wMnOPZy8SKg1sY"
ADMIN_IDS = [6416481890, 7670738203]
UPI_ID = "paytmqr5y7pls@ptys"
FORCE_CHANNEL = "@voucher_zone"

SHEIN_PRICES = {"500":15,"1000":70,"2000":115,"4000":175}
BB_PRICES = {"1":15,"5":13,"10":13,"20":13}

user_state = {}
pending_payments = {}

# ---------------- FILE HELPERS ----------------

def load_json(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def load_data(): return load_json("data.json", {"shein":{}, "bigbasket":{}, "free":[]})
def save_data(d): save_json("data.json", d)

def load_orders(): return load_json("orders.json", {})
def save_orders(d): save_json("orders.json", d)

def load_users(): return load_json("users.json", [])
def save_users(d): save_json("users.json", d)

def load_points(): return load_json("points.json", {})
def save_points(d): save_json("points.json", d)

def load_refs(): return load_json("referrals.json", {})
def save_refs(d): save_json("referrals.json", d)

def load_rewarded(): return load_json("rewarded.json", [])
def save_rewarded(d): save_json("rewarded.json", d)

def load_lottery(): return load_json("lottery.json", {})
def save_lottery(d): save_json("lottery.json", d)

# ---------------- UTIL ----------------

def generate_lottery_token():
    return "GL-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ---------------- MAIN MENU ----------------

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(
    [["🛍 Shein", "🧺 BigBasket"],
     ["🎁 Refer & Earn", "⭐ My Points"],
     ["🎉 Free Code", "📦 My Orders"],
     ["🎟 Golden Lottery"],
     ["🆘 Support"]],
    resize_keyboard=True
)
    if update.message:
        await update.message.reply_text("Welcome! Choose option:", reply_markup=kb)
    else:
        await update.callback_query.message.reply_text("Welcome! Choose option:", reply_markup=kb)

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    users = load_users()
    if uid not in users:
        users.append(uid)
        save_users(users)

    refs = load_refs()

    if args:
        try:
            ref = int(args[0])
            if ref != uid and str(uid) not in refs:
                refs[str(uid)] = ref
                save_refs(refs)
                try:
                    await context.bot.send_message(ref, "🎉 Someone joined using your referral link!")
                except:
                    pass
        except:
            pass

    try:
        m = await context.bot.get_chat_member(FORCE_CHANNEL, uid)
        if m.status in ["member", "administrator", "creator"]:
            await show_main_menu(update, context)
        else:
            raise
    except:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_CHANNEL[1:]}")],
            [InlineKeyboardButton("Verify", callback_data="verify")]
        ])
        await update.message.reply_text("Join & Verify:", reply_markup=kb)

# ---------------- VERIFY ----------------

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.callback_query.from_user.id

    try:
        m = await context.bot.get_chat_member(FORCE_CHANNEL, uid)
        if m.status in ["member", "administrator", "creator"]:
            refs = load_refs()
            points = load_points()
            rewarded = load_rewarded()

            if str(uid) in refs and str(uid) not in rewarded:
                referrer = refs[str(uid)]
                points[str(referrer)] = points.get(str(referrer), 0) + 2
                save_points(points)
                rewarded.append(str(uid))
                save_rewarded(rewarded)

                try:
                    await context.bot.send_message(referrer, "✅ Referral successful!\n🎁 You received +2 points")
                except:
                    pass

            await update.callback_query.message.delete()
            await show_main_menu(update, context)
        else:
            await update.callback_query.answer("Join first!", show_alert=True)
    except:
        await update.callback_query.answer("Join first!", show_alert=True)

# ---------------- GOLDEN LOTTERY ----------------

async def golden_lottery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = (
        "🎟 Golden Lottery Rules\n\n"
        "• Entry Fee: ₹3\n"
         "• Prize Pool bb Code \n"
        "• Each user gets a unique token id\n"
        "• 10-20 Winner announced later\n\n"
        "Click below to participate 👇"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 Get Lottery", callback_data="lottery_pay")]
    ])
    await update.message.reply_text(rules, reply_markup=kb)

async def lottery_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upi = f"upi://pay?pa={UPI_ID}&pn=GoldenLottery&am=3"
    img = qrcode.make(upi)
    path = f"lottery_{update.effective_user.id}.png"
    img.save(path)

    user_state[update.effective_user.id] = "LOTTERY_SCREENSHOT"

    await update.callback_query.message.reply_photo(
        photo=open(path, "rb"),
        caption="Pay ₹3 for Golden Lottery\n\n📸 Send payment screenshot after payment."
    )

# ---------------- SCREENSHOT ----------------

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return   # SAFETY CHECK

    uid = update.effective_user.id
    state = user_state.get(uid)

    if state not in ["WAITING_SCREENSHOT", "LOTTERY_SCREENSHOT"]:
        return

    photo = update.message.photo[-1].file_id
    username = update.effective_user.username or "NoUsername"

    if state == "LOTTERY_SCREENSHOT":
        pending_payments[uid] = {
            "service": "lottery",
            "approved": False,
            "username": username
        }
        msg = f"🎟 Golden Lottery Payment\nUser: {uid}\nUsername: @{username}"

    else:
        service = context.user_data.get("service")
        qty = context.user_data.get("qty", 1)

        pending_payments[uid] = {
            "service": service,
            "qty": qty,
            "approved": False
        }

        msg = f"🧾 New Payment\nUser: {uid}\nService: {service}\nQty: {qty}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve_{uid}")],
        [InlineKeyboardButton("Reject", callback_data=f"reject_{uid}")]
    ])

    for admin in ADMIN_IDS:
        await context.bot.send_photo(admin, photo, caption=msg, reply_markup=kb)

    await update.message.reply_text("⏳ Please wait, admin is verifying...")


    # ---------------- APPROVE ----------------
    if action == "approve":

        # 🎟 GOLDEN LOTTERY (NO STOCK SYSTEM)
        if service == "lottery":
            lottery_db = load_lottery()
            token = generate_lottery_token()

            lottery_db[token] = {
                "user_id": uid,
                "username": username
            }

            save_lottery(lottery_db)

            orders.setdefault(str(uid), [])
            orders[str(uid)].append(f"🎟 Golden Lottery Ticket : {token}")
            save_orders(orders)

            pending_payments[uid]["approved"] = True

            await context.bot.send_message(
                uid,
                f"🎉 Golden Lottery Entry Successful!\n\n"
                f"🎫 Your Ticket ID:\n`{token}`\n\n"
                f"Keep this safe. Winner Will Anounce Soon",
                parse_mode="Markdown"
            )

            await update.callback_query.message.reply_text("Lottery Approved ✅")
            return

        # 🛍 NORMAL COUPON SYSTEM ONLY
        data = load_data()
        qty = pending_payments[uid].get("qty", 1)
        amt = pending_payments[uid].get("amt", "")

        stock = data.get(service, {})
        codes = []

        for k in stock:
            while stock[k] and len(codes) < qty:
                codes.append(stock[k].pop(0))

        if len(codes) == 0:
            await context.bot.send_message(uid, "❌ Out of stock")
            await update.callback_query.message.reply_text("Out of stock ❌")
            return

        save_data(data)

        orders.setdefault(str(uid), [])

        for code in codes:
            if service == "shein":
                label = f"🛍 Shein ₹{amt} : {code}"
            else:
                label = f"🧺 BigBasket x{qty} : {code}"

            orders[str(uid)].append(label)

        save_orders(orders)

        pending_payments[uid]["approved"] = True

        await context.bot.send_message(uid, "✅ Your Codes:\n" + "\n".join(codes))
        await update.callback_query.message.reply_text("Approved & Sent ✅")

    # ---------------- REJECT ----------------
    else:
        pending_payments[uid]["approved"] = True
        await context.bot.send_message(uid, "❌ Payment Rejected")
        await update.callback_query.message.reply_text("Rejected ❌")

    user_state.pop(uid, None)
# ---------------- REFER & EARN ----------------

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    link = f"https://t.me/{context.bot.username}?start={uid}"
    await update.message.reply_text(f"🎁 Refer & Earn\n\nShare this link:\n{link}\n\nYou get 2 points per referral!")

# ---------------- MY POINTS ----------------

async def my_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    points = load_points()
    p = points.get(str(update.effective_user.id), 0)
    await update.message.reply_text(f"⭐ Your Points: {p}")

# ---------------- FREE CODE ----------------

async def free_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 Code - 4 Points", callback_data="free_1")],
        [InlineKeyboardButton("2 Codes - 8 Points", callback_data="free_2")],
        [InlineKeyboardButton("3 Codes - 12 Points", callback_data="free_3")],
        [InlineKeyboardButton("5 Codes - 18 Points", callback_data="free_5")]
    ])
    await update.message.reply_text("🎉 Redeem Free Codes Refer to get points :", reply_markup=kb)

async def free_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qty = int(update.callback_query.data.split("_")[1])
    cost = {1:4, 2:8, 3:12, 5:18}[qty]

    points = load_points()
    uid = str(update.effective_user.id)

    if points.get(uid, 0) < cost:
        await update.callback_query.answer("❌ Not enough points", show_alert=True)
        return

    data = load_data()
    free = data["free"]

    if len(free) < qty:
        await update.callback_query.answer("❌ No free codes left try again tomorrow ", show_alert=True)
        return

    codes = [free.pop(0) for _ in range(qty)]
    points[uid] -= cost

    save_data(data)
    save_points(points)

    await update.callback_query.message.reply_text("🎉 Your Free Codes:\n" + "\n".join(codes))

# ---------- ADMIN PANEL ----------

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("➕ Bulk Add", callback_data="admin_bulk")],
        [InlineKeyboardButton("📦 Check Stock", callback_data="admin_stock")]
    ])

    await update.message.reply_text("👑 Admin Panel", reply_markup=kb)

# ---------- ADMIN BUTTONS ----------

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in ADMIN_IDS:
        return

    data = update.callback_query.data

    if data == "admin_broadcast":
        user_state[uid] = "BROADCAST"
        await update.callback_query.message.reply_text("Send broadcast message:")

    elif data == "admin_bulk":
        user_state[uid] = "BULK"
        await update.callback_query.message.reply_text(
            "Send bulk coupons like:\n"
            "/bulk shein 500\n"
            "CODE1\nCODE2\nCODE3"
        )

    elif data == "admin_stock":
        d = load_data()
        orders = load_orders()

        shein = d["shein"]
        bb = d["bigbasket"]
        free = d.get("free", [])

        total_bb = sum(len(v) for v in bb.values())
        total_free_orders = sum(
            1 for u in orders for o in orders[u] if "Free Code" in o
        )

        msg = (
            "📦 LIVE STOCK STATUS\n\n"
            "Shein Coupons\n"
            f"₹500  → {len(shein['500'])}\n"
            f"₹1000 → {len(shein['1000'])}\n"
            f"₹2000 → {len(shein['2000'])}\n"
            f"₹4000 → {len(shein['4000'])}\n\n"
            "BigBasket Coupons\n"
            f"1 Pack  → {len(bb['1'])}\n"
            f"5 Pack  → {len(bb['5'])}\n"
            f"10 Pack → {len(bb['10'])}\n"
            f"20 Pack → {len(bb['20'])}\n\n"
            "Free Codes\n"
            f"Stock → {len(free)}\n"
            f"Redeemed → {total_free_orders}"
        )

        await update.callback_query.message.reply_text(msg)

# ---------- ADMIN TEXT ----------

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_state.get(uid)

    if uid not in ADMIN_IDS:
        return

    # ---------- BROADCAST ----------
    if state == "BROADCAST":
        users = load_users()
        sent = 0
        failed = 0

        for u in users:
            try:
                await context.bot.send_message(u, update.message.text)
                sent += 1
            except:
                failed += 1

        await update.message.reply_text(
            f"✅ Broadcast Finished\n\n"
            f"Sent: {sent}\n"
            f"Failed: {failed}"
        )

        user_state.pop(uid)

# ---------- BULK ADD ----------

async def bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        lines = update.message.text.split("\n")
        cmd = lines[0].split()

        service = cmd[1].lower()   # shein / bigbasket / free
        key = cmd[2].lower()       # 500 / 1 / any
        codes = lines[1:]

        data = load_data()

        # ---------- FREE CODES ----------
        if service == "free":
            if "free" not in data:
                data["free"] = []

            data["free"].extend(codes)
            save_data(data)

            await update.message.reply_text(f"✅ {len(codes)} free coupons added!")
            return

        # ---------- NORMAL COUPONS ----------
        if service not in data:
            await update.message.reply_text("❌ Invalid service")
            return

        if key not in data[service]:
            data[service][key] = []

        data[service][key].extend(codes)
        save_data(data)

        await update.message.reply_text(f"✅ {len(codes)} coupons added!")

    except:
        await update.message.reply_text(
            "❌ Wrong format!\n\n"
            "Use:\n"
            "/bulk shein 500\nCODE1\nCODE2\n\n"
            "For free codes:\n"
            "/bulk free any\nFREE1\nFREE2"
        )
# ---------- SHEIN ----------

async def shein(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()["shein"]
    buttons = [
        [InlineKeyboardButton(f"₹500 (15rs) | Stock: {len(data['500'])}", callback_data="shein_500")],
        [InlineKeyboardButton(f"₹1000 (70rs) | Stock: {len(data['1000'])}", callback_data="shein_1000")],
        [InlineKeyboardButton(f"₹2000 (115rs) | Stock: {len(data['2000'])}", callback_data="shein_2000")],
        [InlineKeyboardButton(f"₹4000 (175rs) | Stock: {len(data['4000'])}", callback_data="shein_4000")]
    ]
    await update.message.reply_text("Select Shein Amount:", reply_markup=InlineKeyboardMarkup(buttons))

# ---------- BIGBASKET ----------

async def bigbasket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()["bigbasket"]
    buttons = [
        [InlineKeyboardButton("1 - ₹15 per coupon", callback_data="bb_1")],
        [InlineKeyboardButton("5 - ₹13 per coupon", callback_data="bb_5")],
        [InlineKeyboardButton("10 - ₹13 per coupon", callback_data="bb_10")],
        [InlineKeyboardButton("20 - ₹13 per coupon", callback_data="bb_20")]
    ]
    await update.message.reply_text(
        f"📦 Available Stock: {sum(len(v) for v in data.values())}\n\n🛍️ Select how many Bigbasket codes you want to buy:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---------- QR ----------

async def generate_qr(update, context, price, qty, service):
    total = price * qty
    upi = f"upi://pay?pa={UPI_ID}&pn=Coupon&am={total}"

    img = qrcode.make(upi)
    path = f"qr_{update.effective_user.id}.png"
    img.save(path)

    context.user_data["qty"] = qty
    context.user_data["service"] = service
    user_state[update.effective_user.id] = "WAITING_SCREENSHOT"

    await update.callback_query.message.reply_photo(
        photo=open(path,"rb"),
        caption=f"Pay ₹{total}\nQty: {qty}\nUPI: {UPI_ID}\n\n📸 Send payment screenshot here 👇👇"
    )

# ---------- BUTTON HANDLER ----------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    stock_data = load_data()

    if data.startswith("shein_"):
        amt = data.split("_")[1]

        # Check Shein stock
        available = len(stock_data["shein"][amt])

        if available == 0:
            await update.callback_query.answer(
                "❌ Out of stock!", show_alert=True
            )
            return

        context.user_data["amt"] = amt
        await generate_qr(update, context, SHEIN_PRICES[amt], 1, "shein")

    elif data.startswith("bb_"):
        qty = int(data.split("_")[1])

        # Count total BigBasket stock
        total_stock = sum(len(v) for v in stock_data["bigbasket"].values())

        # ❌ Not enough stock
        if total_stock < qty:
            await update.callback_query.answer(
                f"❌ Only {total_stock} coupons available!", show_alert=True
            )
            return

        # ✅ Enough stock
        await generate_qr(update, context, BB_PRICES[str(qty)], qty, "bigbasket")


# ---------------- ADMIN ACTION ----------------

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action, uid = update.callback_query.data.split("_")
    uid = int(uid)

    if uid not in pending_payments:
        await update.callback_query.answer("Payment not found", show_alert=True)
        return

    if pending_payments[uid].get("approved"):
        await update.callback_query.answer("Already approved ✅", show_alert=True)
        return

    orders = load_orders()
    service = pending_payments[uid]["service"]
    username = pending_payments[uid].get("username", "Unknown")

    if action == "approve":

        # 🎟 GOLDEN LOTTERY
        if service == "lottery":
            lottery_db = load_lottery()
            token = generate_lottery_token()

            lottery_db[token] = {
                "user_id": uid,
                "username": username
            }
            save_lottery(lottery_db)

            orders.setdefault(str(uid), [])
            orders[str(uid)].append(f"🎟 Golden Lottery Ticket : {token}")
            save_orders(orders)

            pending_payments[uid]["approved"] = True

            await context.bot.send_message(
                uid,
                f"🎉 Golden Lottery Entry Successful!\n\n"
                f"🎫 Your Ticket ID:\n`{token}`\n\n"
                f"Keep this safe.",
                parse_mode="Markdown"
            )

            await update.callback_query.message.reply_text("Lottery Approved ✅")
            return

    else:
        pending_payments[uid]["approved"] = True
        await context.bot.send_message(uid, "❌ Payment Rejected")
        await update.callback_query.message.reply_text("Rejected ❌")

    user_state.pop(uid, None)



# ---------- MY ORDERS ----------

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = load_orders()
    uid = str(update.effective_user.id)

    if uid not in orders or not orders[uid]:
        await update.message.reply_text("You have no orders yet.")
    else:
        await update.message.reply_text("📦 Your Orders:\n" + "\n".join(orders[uid]))

# ---------- SUPPORT ----------

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 Support:\nContact: @voucherzone_support")

# ---------- ADD COUPON ----------

async def add_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        _, service, key, code = update.message.text.split(" ",3)
        data = load_data()
        data[service][key].append(code)
        save_data(data)
        await update.message.reply_text("Coupon Added ✅")
    except:
        await update.message.reply_text("Use:\n/add shein 500 CODE\n/add bigbasket 1 CODE")
async def bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        lines = update.message.text.split("\n")
        cmd = lines[0].split()

        service = cmd[1]   # shein / bigbasket / free
        key = cmd[2]       # 500 / 1 / any
        codes = lines[1:]

        data = load_data()

        if service not in data:
            await update.message.reply_text("❌ Invalid service")
            return

        if key not in data[service]:
            data[service][key] = []

        data[service][key].extend(codes)
        save_data(data)

        await update.message.reply_text(f"✅ {len(codes)} coupons added!")

    except:
        await update.message.reply_text(
            "❌ Wrong format!\n\n"
            "Use:\n"
            "/bulk shein 500\nCODE1\nCODE2\nCODE3\n\n"
            "For free codes:\n"
            "/bulk free any\nFREE1\nFREE2"
        )

# ---------- HANDLERS ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------- USER COMMANDS ----------
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_coupon))

# ---------- ADMIN COMMANDS ----------
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("bulk", bulk_add))

# ---------- CALLBACK BUTTONS ----------
app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
app.add_handler(CallbackQueryHandler(button_handler, pattern="shein_|bb_"))
app.add_handler(CallbackQueryHandler(admin_action, pattern="approve_|reject_"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="admin_"))
app.add_handler(CallbackQueryHandler(free_handler, pattern="free_"))
app.add_handler(CallbackQueryHandler(lottery_pay, pattern="lottery_pay"))  # 🎟 Golden Lottery

# ---------- MAIN MENU TEXT BUTTONS ----------
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Shein"), shein))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("BigBasket"), bigbasket))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("My Orders"), my_orders))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Support"), support))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Refer"), refer))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Points"), my_points))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Free"), free_code))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Golden"), golden_lottery))  # 🎟 Lottery

# ---------- ADMIN TEXT INPUT (ONLY FOR ADMINS) ----------
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_IDS),
        admin_text
    )
)

# ---------- SCREENSHOT (PAYMENT / LOTTERY) ----------
app.add_handler(MessageHandler(filters.PHOTO, receive_screenshot))

print("Bot Running...")
app.run_polling()


