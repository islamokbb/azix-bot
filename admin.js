const TelegramBot = require("node-telegram-bot-api");
const fs = require("fs");

// =============== CONFIG ===============
const ADMIN_BOT_TOKEN = process.env.ADMIN_BOT_TOKEN;
const ADMIN_ID = 7771891436;
const DATA_FILE = "papers.json";

// =============== INIT ===============
const bot = new TelegramBot(ADMIN_BOT_TOKEN, { polling: true });

if (!fs.existsSync(DATA_FILE)) {
  fs.writeFileSync(DATA_FILE, JSON.stringify([]));
}

// =============== START ===============
bot.onText(/\/start/, (msg) => {
  if (msg.from.id !== ADMIN_ID) {
    return bot.sendMessage(msg.chat.id, "⛔ غير مصرح");
  }

  bot.sendMessage(msg.chat.id, "🛠 لوحة التحكم", {
    reply_markup: {
      keyboard: [
        ["➕ إضافة ورقة"],
        ["👀 عرض أوراق اليوم"],
        ["🗑 مسح أوراق اليوم"]
      ],
      resize_keyboard: true
    }
  });
});

// =============== HANDLER ===============
bot.on("message", (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  if (msg.from.id !== ADMIN_ID) return;

  // إضافة ورقة
  if (text === "➕ إضافة ورقة") {
    bot.sendMessage(chatId, "✏️ اكتب الرهان الآن:");
    bot.once("message", (m) => {
      const papers = JSON.parse(fs.readFileSync(DATA_FILE));
      papers.push("• " + m.text);
      fs.writeFileSync(DATA_FILE, JSON.stringify(papers, null, 2));
      bot.sendMessage(chatId, "✅ تم إضافة الورقة");
    });
  }

  // عرض الأوراق
  if (text === "👀 عرض أوراق اليوم") {
    const papers = JSON.parse(fs.readFileSync(DATA_FILE));
    if (papers.length === 0) {
      return bot.sendMessage(chatId, "📭 لا توجد أوراق");
    }
    bot.sendMessage(chatId, "📰 أوراق اليوم:\n\n" + papers.join("\n"));
  }

  // مسح الأوراق
  if (text === "🗑 مسح أوراق اليوم") {
    fs.writeFileSync(DATA_FILE, JSON.stringify([]));
    bot.sendMessage(chatId, "🗑 تم مسح جميع الأوراق");
  }
});

console.log("✅ Admin bot running");
