# Nespresso integration for Home Assistant

A custom integration that pulls live status from your Nespresso smart
machine via the official cloud API (`nespresso.com/ecapi`) — the same
backend used by the Nespresso app. No local hub, no Bluetooth.

> ⚠️ **Unofficial project.** Not affiliated with, endorsed by, or
> supported by Nespresso/Nestlé. The API is undocumented and
> reverse-engineered from the mobile app traffic — it can change or
> stop working without notice. Use at your own risk.

---

## What you get

**Sensors**
- Machine status (off / on / heating / ready / brewing / cleaning / standby...)
- Last brewed coffee type
- Configured water hardness
- Error code
- Main + connectivity firmware versions
- Last presence update timestamp

**Binary sensors**
- Cloud connectivity
- Descaling alert
- Generic error flag

Everything is currently **read-only** — there's no support yet for
triggering brews or sending commands remotely.

---

## Setup

### 1. Get your access tokens

The integration authenticates using the same session cookies your
browser uses when you're logged into nespresso.com:

1. Log into nespresso.com in Chrome/Edge.
2. Open DevTools (`F12`) → **Network** tab.
3. Reload the page or log in again so the **login** POST request shows up.
4. Click it → **Headers** → scroll to **Response Headers** → **Set-Cookie**.
5. Grab two values:
   - `access-token` (a long JWT)
   - `refresh-token` (a short UUID, optional but recommended)

### 2. Install the integration

Via HACS:
- Add this repo as a custom repository
- Install "Nespresso"
- Restart Home Assistant

Manual:
- Drop the `custom_components/nespresso/` folder into your HA config
- Restart

### 3. Configure

Go to **Settings → Devices & Services → Add Integration → Nespresso**,
paste your tokens, pick your market/country, done.

---

## Token refresh

If you supply a refresh token, the integration tries to silently renew
the access token when it expires. If refresh fails (or you didn't
provide one), you'll get a notification asking you to redo the steps
above.

---

## Known limitations

- No write operations (descaling, settings, brewing) yet
- Water hardness can apparently be *set* via the API but not always
  read back reliably
- Endpoint paths and field names may shift if Nespresso updates their
  backend — open an issue if something breaks

---

## License

MIT
