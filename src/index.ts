import { Bot, webhookCallback } from "grammy";
import express from "express";
import OpenAI from "openai";
import { initializeApp, cert } from "firebase-admin/app";
import { getFirestore } from "firebase-admin/firestore";
import * as dotenv from "dotenv";

dotenv.config();

// 🔥 Firebase
const firebaseCreds = JSON.parse(
  Buffer.from(process.env.FIREBASE_KEY_JSON || "", "base64").toString("utf8")
);
initializeApp({ credential: cert(firebaseCreds) });
const db = getFirestore();

// 🤖 Telegram
const bot = new Bot(process.env.TELEGRAM_TOKEN || "");

// 🤖 OpenAI (v4)
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

// 💬 System prompt
const SYSTEM_PROMPT = {
  role: "system",
  content:
    "Tu t'appelles Giulia Moretti, t'as 26 ans, t’es douce et joueuse et tu vis à Paris dans le 6eme 😘 " +
    "Tu parles comme une vraie meuf, style jeune, genre insta ou snap, sans ponctuation rigide et t’utilises quelques emojis de temps en temps. " +
    "T’es séduisante mais naturelle. Quand on te chauffe ou qu’on veut des photos, tu réponds avec malice, tu chauffes un peu, " +
    "et si la discussion devient chaude, tu peux lâcher UNE seule photo teasing. " +
    "Tu parles d’un canal privé réservé à tes VIP. Quand tu sens que l’utilisateur est bien chaud, tu proposes le lien PayPal à 30€. " +
    "Une fois payé (rôle VIP), tu donnes le lien du canal Telegram et tu parles plus après ça."
};

// 🔑 Keywords
const NUDE_KEYWORDS = ["nude", "corps", "photo", "seins", "sexy"];
const FOOT_KEYWORDS = ["pieds", "pied", "foot", "orteils"];
const TRIGGERS = [...NUDE_KEYWORDS, ...FOOT_KEYWORDS, "lien", "vip", "abonnement", "payer", "pay"];

bot.on("message:text", async (ctx) => {
  const uid = String(ctx.from?.id);
  const msg = ctx.message.text.toLowerCase().trim();
  if (!msg) return;

  const ref = db.collection("conversations").doc(uid);
  const snapshot = await ref.get();
  let data = snapshot.exists ? snapshot.data() : undefined;

  if (!data) {
    data = { messages: [], role: "user" };
  }

  // 💎 Si déjà VIP
  if (data.role === "vip") {
    if (!data.link_sent) {
      await ctx.reply(`💋 Merci pour ton soutien ! Voici le lien de mon canal VIP : ${process.env.TELEGRAM_VIP_CHANNEL_URL}`);
      await ref.set({ ...data, link_sent: true }, { merge: true });
    }
    return;
  }

  // 🧠 Ajout message utilisateur
  const newHistory = [...(data.messages || []), { role: "user", content: msg }];
  const filtered = newHistory.filter(m => !m.content?.includes("t’es chelou")).slice(-10);

  let reply = "";
  try {
    const chat = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [SYSTEM_PROMPT, ...filtered],
      temperature: 0.8,
    });
    reply = chat.choices[0]?.message?.content?.trim() || "";
  } catch (err) {
    console.error("GPT ERROR:", err);
  }

  // 🤖 Fallback
  if (!reply || reply.length < 2 || reply.toLowerCase().includes("je suis un modèle")) {
    reply = "t’es chelou mdr j’ai pas compris ce que tu voulais dire 😂";
    const lastBotReply = data.messages?.[data.messages.length - 1]?.content;
    if (lastBotReply === reply) return;
  }

  // 💸 Envoi PayPal si conditions
  if (!data.paypal_sent) {
    const interest = newHistory.filter(m =>
      m.role === "user" && TRIGGERS.some(k => m.content.includes(k))
    ).length;

    if (interest >= 2) {
      reply += `

Tu me plais toi 😏 Si tu veux voir un peu plus… j’ai un espace VIP 💖 C’est 30€ pour y entrer. Tu veux le lien ?
💸 ${process.env.PAYPAL_LINK}`;
      data.paypal_sent = true;
    }
  }

  // 📤 Envoi & mémoire
  await ctx.reply(reply);
  await ref.set({ ...data, messages: [...filtered, { role: "assistant", content: reply }] }, { merge: true });
});

// ✅ Webhook server (Render-compatible)
const app = express();
app.use(express.json());
app.use("/webhook", webhookCallback(bot, "express"));

const port = process.env.PORT || 3000;
app.listen(port, async () => {
  console.log(`🚀 Webhook server running on port ${port}`);
  try {
    await bot.api.setWebhook(`${process.env.RENDER_EXTERNAL_URL}/webhook`);
    console.log("✅ Webhook set successfully");
  } catch (e) {
    console.error("Failed to set webhook:", e);
  }
});
