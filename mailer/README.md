# Mailer

A private, self-hosted tool for sending marketing emails to your contact list through Amazon SES, with a team dashboard showing deliveries, opens, clicks, bounces and unsubscribes.

- Runs on your Windows PC; your team uses it from their browsers.
- Import contacts from CSV, organise them into lists, write campaigns in a visual editor, send a test, then send now or schedule.
- Every email gets your postal address and a one-click unsubscribe link (hosted by Amazon, so your PC never has to be reachable from the internet).
- Unsubscribes, hard bounces and spam complaints are suppressed automatically and never re-imported by mistake.
- Live campaign reports: delivered, opened, clicked, top links, bounces, unsubscribes, per-recipient detail.
- Roles: **admin** (team + settings), **editor** (campaigns + contacts), **viewer** (reports only).

---

## 1. Install (once)

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/>. On the first installer screen, tick **"Add python.exe to PATH"**.
2. Copy the `mailer` folder somewhere permanent, e.g. `C:\Mailer`.
3. Double-click **`setup.bat`**. It creates a private Python environment, installs everything and creates your `.env` settings file.
4. Double-click **`start.bat`** and open <http://localhost:8080>.

The app starts in **demo mode**: nothing is really sent and the stats are simulated, so you can try everything safely. Create your admin account, fill in **Settings**, import a CSV and send a campaign to see how it works.

## 2. Set up Amazon SES (once, about 30 minutes plus waiting)

### 2a. AWS account and access keys

1. Create an AWS account at <https://aws.amazon.com> if you don't have one.
2. Pick a region close to you and use it throughout, e.g. **Europe (London) `eu-west-2`** or **US East (N. Virginia) `us-east-1`**.
3. In the AWS console open **IAM → Users → Create user**, name it `mailer`.
4. Choose **Attach policies directly** and attach: `AmazonSESFullAccess`, `AmazonSNSFullAccess`, `AmazonSQSFullAccess`.
5. Open the user → **Security credentials → Create access key → "Application running outside AWS"**. Copy both keys.
6. Open `.env` in Notepad and fill in:

   ```
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   AWS_REGION=eu-west-2
   ```

   Keep `.env` private: anyone with these keys can send email as you.

### 2b. Create the AWS resources

Open a terminal in the `mailer` folder (in File Explorer, type `cmd` in the address bar and press Enter), then run:

```
.venv\Scripts\python manage.py setup-aws
```

This creates, in one go:

- an SES configuration set with open and click tracking,
- an SNS topic + SQS queue that collect delivery/open/click/bounce/unsubscribe events (kept for 14 days, so nothing is lost while your PC is off),
- an SES contact list that powers the hosted one-click unsubscribe page.

### 2c. Verify your domain

```
.venv\Scripts\python manage.py verify-domain yourdomain.com
```

It prints six DNS records. Add them where your domain's DNS is managed (GoDaddy, Cloudflare, Namecheap, 123-reg…):

| Record | Why |
| --- | --- |
| 3 × CNAME `…._domainkey` | **DKIM**: proves emails really come from your domain |
| MX + TXT on `bounce.yourdomain.com` | **SPF / custom MAIL FROM**: bounces come back to Amazon, and SPF aligns with your domain |
| TXT `_dmarc` | **DMARC**: required by Gmail and Yahoo for bulk senders |

Check progress (it can take from minutes up to 72 hours):

```
.venv\Scripts\python manage.py domain-status yourdomain.com
```

> Already have a DMARC record? Keep yours and don't add a second one.

### 2d. Request production access

New SES accounts start in the **sandbox**: they can only send to addresses you've verified, up to 200 a day. In the SES console go to **Account dashboard → Request production access** and describe your use:

> Monthly marketing newsletter (1–2 per month) to a few thousand customers who opted in. We use SES list management for one-click unsubscribe and automatically suppress bounces and complaints.

Approval usually takes about 24 hours. **Settings → Check connection** in the app shows your status and limits.

### 2e. Switch to live sending

In `.env` set `MAIL_BACKEND=ses`, then close and re-open `start.bat`. The yellow demo banner disappears.

In **Settings**, use a From address on your verified domain (e.g. `news@yourdomain.com`) and add your postal address.

**Warm up your domain.** For the first couple of campaigns, send to your most engaged contacts first (e.g. a list of recent customers) before the whole list. Inbox providers trust new domains gradually.

## 3. Day-to-day use

1. **Contacts → Import CSV.** Only an `email` column is required; `first_name`, `last_name` and any other columns are stored too.
2. **Campaigns → New campaign.** Write the email, choose lists, save.
3. **Send a test** to yourself and check it on your phone and desktop.
4. **Save & continue to send**: send now, or schedule (your PC must be on at that time).
5. Watch the report update live. Opens and clicks keep arriving for days.

Personalisation: `{{ first_name }}`, `{{ last_name }}`, `{{ email }}` and any CSV column, e.g. `{{ company }}`. Fallbacks: `{{ first_name or "there" }}`.

About open rates: Apple Mail pre-loads images (inflating opens) and some apps block them (hiding opens). Treat open rate as a trend and click rate as the reliable number.

## 4. Team access

Add people under **Team** and give each their own login.

**Same office / network.** When Mailer starts it prints a "For your team (LAN)" address such as `http://192.168.1.20:8080`. Teammates open that in their browser. The first time, Windows asks whether to allow Python through the firewall. Allow it on **Private networks** only.

**Remote teammates.** Install [Tailscale](https://tailscale.com) (free for small teams) on your PC and on each teammate's computer, signed in to the same Tailscale network. They then open `http://<your-pc-name>:8080`. This is encrypted and private; nothing is exposed to the public internet.

**Do not** forward port 8080 on your router: that would put the login page on the open internet.

Your PC must be on and `start.bat` running for anyone to use Mailer or for scheduled campaigns to send. To start it automatically, put a shortcut to `start.bat` in your Startup folder (press `Win + R`, type `shell:startup`, press Enter).

## 5. Backups and maintenance

- Everything lives in `data\mailer.db`. Back it up by copying the `data` folder while Mailer is stopped (or use OneDrive/Dropbox on a copy).
- Logs are in `data\mailer.log`.
- Locked out? `.venv\Scripts\python manage.py reset-password you@yourdomain.com`
- To update the code later, replace everything except `.env` and `data\`, then run `setup.bat` again.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Campaign **Paused** with "not verified" | Your From domain isn't verified yet (`domain-status`), or the account is still in the sandbox. Fix it, then press **Resume**. |
| Campaign paused with "quota" | You hit the SES daily limit. Press **Resume** tomorrow, or ask AWS for a higher quota. |
| No opens/clicks showing | Check `MAIL_BACKEND=ses`, that `setup-aws` ran without errors, and look in `data\mailer.log`. |
| Teammates can't connect | Same network? Windows firewall allowed? Try `http://<ip>:8080` exactly as printed at startup. |
| "Form expired" | The page was open a long time. Refresh and try again. |

## How it works

```
Browser ──► Mailer (Flask + Waitress, SQLite)  ──send──►  Amazon SES ──► recipients
                    ▲                                         │
                    └── polls ── SQS queue ◄── SNS ◄── events (delivery, open, click,
                                                        bounce, complaint, unsubscribe)
```

- `app/sender.py` freezes the recipient list when a campaign starts, then sends one email at a time just under your SES rate limit. Each send is saved immediately, so a restart resumes exactly where it stopped without duplicates.
- `app/tracking.py` applies SES events to each recipient and suppresses hard bounces, complaints and unsubscribes. Every 30 minutes it also re-syncs opt-outs from the SES contact list as a safety net.
- `app/worker.py` runs both loops as background threads next to the web server.

Development: `pip install pytest` then `pytest` runs the test suite.
