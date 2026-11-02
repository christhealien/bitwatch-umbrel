// Gotify notifications for Bitwatch (added by bitwatch-umbrel). Settings live in db.gotify:
//   { url, token, priority, linkBase }   url = Gotify server, token = an *application* token from Gotify.
import memory from "./memory.js";
import logger from "./logger.js";
import { formatSats } from "./telegramActions.js";

const sentAlerts = new Map();
const LABELS = {
  chain_in: "Received (confirmed)",
  chain_out: "Sent (confirmed)",
  mempool_in: "Incoming (mempool)",
  mempool_out: "Outgoing (mempool)",
};

const config = () => memory.db.gotify || {};
export const isConfigured = (c = config()) => Boolean(c.url && c.token);

export const send = async (c, title, message, extras) => {
  const base = String(c.url || "").trim().replace(/\/+$/, "");
  const priority = Number.isFinite(Number(c.priority)) ? Number(c.priority) : 8;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 10000);
  try {
    const res = await fetch(`${base}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Gotify-Key": String(c.token).trim() },
      body: JSON.stringify({ title, message, priority, ...(extras ? { extras } : {}) }),
      signal: ctrl.signal,
    });
    if (!res.ok) {
      const text = (await res.text().catch(() => "")).slice(0, 200);
      const err = new Error(`Gotify answered ${res.status}${text ? `: ${text}` : ""}${res.status === 401 ? " (check the application token)" : ""}`);
      err.fromGotify = true;
      throw err;
    }
    return true;
  } catch (e) {
    if (e.fromGotify) throw e;
    const why =
      e.name === "AbortError"
        ? "timed out after 10 s"
        : e.cause?.code || e.cause?.errors?.[0]?.code || e.cause?.message || e.message;
    throw new Error(`Could not reach Gotify at ${base} (${why})`);
  } finally {
    clearTimeout(timer);
  }
};

export const test = async (c) => {
  await send(c, "Bitwatch connected", "Gotify notifications are on. Balance changes on your watched addresses will show up here.", {
    "client::display": { contentType: "text/plain" },
  });
  return true;
};

export const notifyBalanceChange = async (address, changes, collection, name) => {
  const c = config();
  if (!isConfigured(c)) return false;
  const lines = [];
  for (const type of ["mempool_in", "mempool_out", "chain_in", "chain_out"]) {
    const value = changes?.[type];
    if (typeof value !== "number") continue;
    const key = `${collection}/${name}/${address}/${type}:${value}`;
    if (sentAlerts.has(key)) continue;
    sentAlerts.set(key, true);
    lines.push(`${LABELS[type]}: ${formatSats(value)}`);
  }
  if (!lines.length) return true;
  const base = String(c.linkBase || "").trim().replace(/\/+$/, "");
  const link = base ? `${base}/address/${address}` : "";
  const message = `${collection} / ${name}\n${address}\n\n${lines.join("\n")}${link ? `\n\n${link}` : ""}`;
  const extras = { "client::display": { contentType: "text/plain" } };
  if (link) extras["client::notification"] = { click: { url: link } };
  try {
    await send(c, `Balance change: ${name || collection}`, message, extras);
    logger.info(`Gotify alert sent: ${collection}/${name} (${address})`);
    return true;
  } catch (e) {
    logger.error(`Gotify alert failed: ${e.message}`);
    return false;
  }
};

export const cleanup = () => sentAlerts.clear();

export default { isConfigured, send, test, notifyBalanceChange, cleanup };
