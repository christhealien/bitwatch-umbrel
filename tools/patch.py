#!/usr/bin/env python3
"""Apply the bitwatch-umbrel changes to a checkout of zapomatic/bitwatch (path given as argv[1]):
Gotify notifications next to Telegram, and the blake2b monochrome look. Core anchors are fatal so a changed
upstream fails the build loudly instead of shipping without Gotify."""
import os, re, shutil, sys

UP = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.join(HERE, "..", "overlay")


def rd(p):
    with open(os.path.join(UP, p), encoding="utf-8") as f:
        return f.read()


def wr(p, s):
    with open(os.path.join(UP, p), "w", encoding="utf-8") as f:
        f.write(s)


def sub(p, old, new, fatal=True, count=1):
    s = rd(p)
    if old not in s:
        msg = f"{p}: anchor not found: {old[:70]!r}"
        if fatal:
            sys.exit("FATAL " + msg)
        print("warn " + msg)
        return
    wr(p, s.replace(old, new, count))


# ---- overlay files
for root, _, files in os.walk(OVERLAY):
    for fn in files:
        src = os.path.join(root, fn)
        dst = os.path.join(UP, os.path.relpath(src, OVERLAY))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)

# ---- server: send alerts to Gotify as well
p = "server/lib/handleBalanceUpdate.js"
sub(p, 'import telegram from "./telegram.js";', 'import telegram from "./telegram.js";\nimport gotify from "./gotify.js";')
s = rd(p)
m = re.search(r"telegram\.notifyBalanceChange\(\s*address,\s*changes,\s*collectionName,\s*addr\.name,\s*chatId\s*\);", s)
if not m:
    sys.exit(f"FATAL {p}: telegram.notifyBalanceChange call not found")
s = s[: m.end()] + "\n    gotify.notifyBalanceChange(address, changes, collectionName, addr.name);" + s[m.end():]
wr(p, s)

p = "server/io/getIntegrations.js"
sub(p, "return { telegram: memory.db.telegram || {} };", "return { telegram: memory.db.telegram || {}, gotify: memory.db.gotify || {} };")

p = "server/io/saveIntegrations.js"
sub(p, 'import telegram from "../lib/telegram.js";', 'import telegram from "../lib/telegram.js";\nimport gotify from "../lib/gotify.js";')
sub(p, "  memory.db.telegram = data.telegram;", """  // Gotify: keep only the known fields; send a test message whenever it is configured and saved
  const g = data.gotify || {};
  memory.db.gotify = {
    url: String(g.url || "").trim(),
    token: String(g.token || "").trim(),
    priority: Number.isFinite(Number(g.priority)) ? Number(g.priority) : 8,
    linkBase: String(g.linkBase || "").trim(),
  };
  if (gotify.isConfigured(memory.db.gotify)) {
    try {
      await gotify.test(memory.db.gotify);
      logger.success("Gotify test message sent");
    } catch (e) {
      logger.error(`Gotify test failed: ${e.message}`);
      memory.saveDb();
      return { error: `Gotify: ${e.message}` };
    }
  }

  memory.db.telegram = data.telegram;""")

# ---- client: Gotify section on the Integrations page, real error text
p = "client/src/Integrations.js"
sub(p, ': "Failed to create telegram bot. Check credentials and try again.",',
    ': response.error || "Failed to save integrations. Check the settings and try again.",')
GOTIFY_UI = r'''
          <hr className="b2b-divider" />
          <div className="data-item">
            <Typography variant="h6" className="crystal-heading">
              Gotify
            </Typography>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <p className="b2b-gotify-note">
                In Gotify open <b>Apps</b>, create an application (for example "Bitwatch") and paste its token here.
                With the Gotify (blake2b) app on the same Umbrel the server address is{" "}
                <code>http://blake2b-gotify_server_1</code>. Saving sends a test message.
              </p>
              <div>
                <Typography component="label" htmlFor="gotify-url" className="crystal-label">
                  Server address
                </Typography>
                <input
                  id="gotify-url"
                  className="crystal-input"
                  value={config.gotify?.url ?? ""}
                  onChange={(e) => handleChange("gotify", "url", e.target.value)}
                  placeholder="http://blake2b-gotify_server_1"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <Typography component="label" htmlFor="gotify-token" className="crystal-label">
                  Application token
                </Typography>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    id="gotify-token"
                    className="crystal-input"
                    type="password"
                    autoComplete="off"
                    value={config.gotify?.token || ""}
                    onChange={(e) => handleChange("gotify", "token", e.target.value)}
                    placeholder="Token of a Gotify application"
                    style={{ flex: 1 }}
                  />
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleChange("gotify", "token", "")}
                    disabled={!config.gotify?.token}
                    className="crystal-button"
                  >
                    Clear
                  </Button>
                </div>
              </div>
              <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                <div style={{ flex: "0 0 160px" }}>
                  <Typography component="label" htmlFor="gotify-priority" className="crystal-label">
                    Priority (0 to 10)
                  </Typography>
                  <input
                    id="gotify-priority"
                    className="crystal-input"
                    type="number"
                    min="0"
                    max="10"
                    value={config.gotify?.priority ?? 8}
                    onChange={(e) => handleChange("gotify", "priority", e.target.value)}
                    style={{ width: "100%" }}
                  />
                </div>
                <div style={{ flex: "1 1 260px" }}>
                  <Typography component="label" htmlFor="gotify-link" className="crystal-label">
                    Link in alerts (optional, opens when you tap the notification)
                  </Typography>
                  <input
                    id="gotify-link"
                    className="crystal-input"
                    value={config.gotify?.linkBase || ""}
                    onChange={(e) => handleChange("gotify", "linkBase", e.target.value)}
                    placeholder="http://umbrel.local:8792"
                    style={{ width: "100%" }}
                  />
                </div>
              </div>
            </div>
          </div>
'''
s = rd(p)
anchor = '          <Box sx={{ mt: 3, display: "flex", justifyContent: "flex-end" }}>'
if s.count(anchor) != 1:
    sys.exit(f"FATAL {p}: save-button anchor found {s.count(anchor)} times")
wr(p, s.replace(anchor, GOTIFY_UI + anchor))

# ---- look: monochrome. Literal colours first (JS + CSS), then the theme stylesheet loaded last.
COLOURS = [
    (r"rgba\(77,\s*244,\s*255,", "rgba(255, 255, 255,"),
    (r"rgba\(255,\s*97,\s*216,", "rgba(255, 255, 255,"),
    (r"rgba\(234,\s*103,\s*246,\s*[\d.]+\)", "rgba(255, 255, 255, 0.25)"),
    (r"rgba\(191,\s*123,\s*233,\s*[\d.]+\)", "rgba(255, 255, 255, 0.25)"),
    (r"rgba\(42,\s*27,\s*80,", "rgba(12, 12, 12,"),
    (r"rgba\(26,\s*16,\s*64,", "rgba(0, 0, 0,"),
    (r"rgba\(20,\s*20,\s*30,", "rgba(10, 10, 10,"),
    (r"rgba\(123,\s*255,\s*160,", "rgba(61, 214, 140,"),
    (r"rgba\(39,\s*174,\s*96,", "rgba(61, 214, 140,"),
    (r"rgba\(255,\s*(?:87|77),\s*(?:87|77),", "rgba(255, 107, 107,"),
    (r"#ff61d8\b", "#f4f4f4"), (r"#4df4ff\b", "#bdbdbd"), (r"#b6f7ff\b", "#e0e0e0"),
    (r"#ff9b3d\b", "#f0b429"), (r"#ff5757\b", "#ff6b6b"), (r"#7bffa0\b", "#3dd68c"),
    (r"#1a1040\b", "#000000"), (r"#2a1b50\b", "#0c0c0c"), (r"#4CAF50\b", "#3dd68c"),
]
n = 0
for root, _, files in os.walk(os.path.join(UP, "client", "src")):
    for fn in files:
        if not fn.endswith((".js", ".jsx", ".css")):
            continue
        fp = os.path.join(root, fn)
        with open(fp, encoding="utf-8") as f:
            s = f.read()
        o = s
        for pat, rep in COLOURS:
            s = re.sub(pat, rep, s, flags=re.I)
        if s != o:
            n += 1
            with open(fp, "w", encoding="utf-8") as f:
                f.write(s)
print(f"recoloured {n} client files")

p = "client/src/index.js"
s = rd(p)
if "blake2b-theme.css" not in s:
    # imported after everything else so it wins
    lines = s.split("\n")
    last = max(i for i, l in enumerate(lines) if l.startswith("import "))
    lines.insert(last + 1, 'import "./blake2b-theme.css";')
    wr(p, "\n".join(lines))
print("bitwatch-umbrel patch applied")
