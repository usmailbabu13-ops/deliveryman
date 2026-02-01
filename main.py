import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserNotParticipant
from motor.motor_asyncio import AsyncIOMotorClient

# ------------------- কনফিগারেশন (সরাসরি এখানে দেয়া আছে) -------------------
API_ID = 35252267
API_HASH = "41a9bafd2a2d7cc342e12a939b920333"
BOT_TOKEN = "8511714924:AAHpLzixant6AdEyYQjAx3b4U5KvNKH6_EY"
DB_CHANNEL_ID = -1003736125534
OWNER_ID = 7224491737

# Advanced Configs
MONGO_URL = "mongodb+srv://deliveryman_DB:Babu1234@cluster0.b1tmwzo.mongodb.net/?appName=Cluster0"
FORCE_SUB_CHANNEL = 0  # 0 মানে Force Subscribe বন্ধ, চ্যানেল ID দিলে চালু হবে
FORCE_SUB_LINK = "https://t.me/flixzonepublic"
AUTO_DELETE_TIME = 1800  # ৩০ মিনিট (সেকেন্ডে)

# ------------------- ডাটাবেস কানেকশন (MongoDB) -------------------
# মঙ্গোডিবি কানেক্ট না থাকলে বট বন্ধ হবে না, শুধু ব্রডকাস্ট কাজ করবে না
try:
    db_client = AsyncIOMotorClient(MONGO_URL)
    db = db_client["MaTelecomBot"]
    users_col = db["users"]
    print("✅ Database Connected!")
except:
    print("⚠️ Database Not Connected! Broadcast won't work.")
    users_col = None

async def add_user(user_id):
    if users_col is not None:
        if not await users_col.find_one({"user_id": user_id}):
            await users_col.insert_one({"user_id": user_id})

# ------------------- বট সেটআপ -------------------
app = Client("MaTelecomPro", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ------------------- এনকোডিং সিস্টেম -------------------
def encode(string):
    string_bytes = str(string).encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return base64_bytes.decode("ascii").strip("=")

def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    return string_bytes.decode("ascii")

# ------------------- FORCE SUBSCRIBE CHECK 🔒 -------------------
async def is_subscribed(client, user_id):
    if FORCE_SUB_CHANNEL == 0: 
        return True
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ["creator", "administrator", "member"]
    except UserNotParticipant:
        return False
    except Exception:
        return True

# ------------------- ইউজার সাইড হ্যান্ডলার -------------------
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    if users_col is not None:
        await add_user(user_id) 
    
    text = message.text
    
    # ১. FSub চেক (Feature 1)
    if not await is_subscribed(client, user_id):
        return await message.reply_text(
            "⚠️ **ভিডিও দেখতে হলে আগে আমাদের চ্যানেলে জয়েন করুন!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=FORCE_SUB_LINK)],
                [InlineKeyboardButton("✅ Try Again", url=f"https://t.me/{client.me.username}?start={text.split(' ')[1] if len(text) > 7 else ''}")]
            ])
        )

    # ২. ভিডিও ডেলিভারি
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
            decoded_string = decode(base64_string)
            
            # ৩. ব্যাচ বা কালেকশন চেক (Feature 3)
            if "batch" in decoded_string:
                _, start_id, end_id = decoded_string.split("_")
                messages_to_send = list(range(int(start_id), int(end_id) + 1))
                status_msg = await message.reply(f"📦 **কালেকশন ({len(messages_to_send)} টি ফাইল) পাঠানো হচ্ছে...**")
            else:
                messages_to_send = [int(decoded_string)]
                status_msg = await message.reply("🔄 **ফাইল প্রসেসিং হচ্ছে...**")

            # ফাইল পাঠানো এবং অটো ডিলিট (Feature 4)
            for msg_id in messages_to_send:
                try:
                    copy = await client.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=DB_CHANNEL_ID,
                        message_id=msg_id,
                        protect_content=True,
                        caption=f"✅ **Powered by Ma Telecom**\n⏳ *This file will delete in {int(AUTO_DELETE_TIME/60)} mins*"
                    )
                    asyncio.create_task(auto_delete(copy))
                    if len(messages_to_send) > 1: await asyncio.sleep(3) 
                except Exception as e:
                    print(f"Failed: {e}")
            
            await status_msg.delete()
        except:
            await message.reply("❌ লিংকটি ভুল অথবা ফাইল ডিলিট হয়েছে।")
    else:
        await message.reply_text(
            f"👋 **{message.from_user.first_name}**, আমি Ma Telecom এর ফাইল বট।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=FORCE_SUB_LINK)]])
        )

# অটো ডিলিট টাইমার
async def auto_delete(message):
    await asyncio.sleep(AUTO_DELETE_TIME)
    try:
        await message.delete()
    except:
        pass

# ------------------- অ্যাডমিন কমান্ডস -------------------

# সিঙ্গেল ভিডিও আপলোড
@app.on_message(filters.private & filters.user(OWNER_ID) & (filters.document | filters.video | filters.audio))
async def single_upload(client, message):
    copied = await message.copy(chat_id=DB_CHANNEL_ID)
    code = encode(str(copied.id))
    link = f"https://t.me/{client.me.username}?start={code}"
    await message.reply(f"🎬 **Link:** `{link}`", disable_web_page_preview=True)

# ব্যাচ লিংক: /batch [Link1] [Link2]
@app.on_message(filters.command("batch") & filters.user(OWNER_ID))
async def batch_handler(client, message):
    try:
        args = message.text.split()
        start_id = int(args[1].split("/")[-1])
        end_id = int(args[2].split("/")[-1])
        batch_string = f"batch_{start_id}_{end_id}"
        link = f"https://t.me/{client.me.username}?start={encode(batch_string)}"
        await message.reply(f"📦 **Batch Link:** `{link}`", disable_web_page_preview=True)
    except:
        await message.reply("⚠️ ভুল কমান্ড! `/batch FirstLink LastLink` ব্যবহার করুন।")

# ব্রডকাস্ট (Feature 2)
@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID) & filters.reply)
async def broadcast(client, message):
    if users_col is None:
        return await message.reply("❌ ডাটাবেস (MongoDB) সেট করা নেই!")
    status = await message.reply("📢 **Broadcast Started...**")
    count = 0
    async for user in users_col.find({}):
        try:
            await message.reply_to_message.copy(chat_id=user['user_id'])
            count += 1
            await asyncio.sleep(0.5)
        except:
            pass
    await status.edit(f"✅ **Sent to {count} users.**")

print("Bot Started!")
app.run()