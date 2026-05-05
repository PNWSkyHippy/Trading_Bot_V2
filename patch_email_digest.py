patch = '''
Fixes:
1. Email only fires on NEW signals hitting the billboard (escalation >= 0 from watchlist)
   and on ROCKET escalations (level 3). Everything else is digested.
2. Digest sends every 2 hours with a summary of all signals since last digest.
3. Per-symbol cooldown extended from 10min to 30min.
4. update_signal_tracking never sends emails - its just CSV tracking.
'''

with open('BreakoutScanner.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ── Fix 1: Add digest queue to AlertSystem.__init__ ──────────────────────────
old_init = '''        self.alert_queue      = queue.Queue()
        self.alert_history:   List[Alert] = []
        self.email_last_sent: Dict[str, datetime] = {}
        self.gui              = None
        self.running          = False'''

new_init = '''        self.alert_queue      = queue.Queue()
        self.alert_history:   List[Alert] = []
        self.email_last_sent: Dict[str, datetime] = {}
        self.gui              = None
        self.running          = False
        # Digest queue: buffer non-urgent emails, flush every 2 hours
        self._digest_queue:   List[str] = []
        self._digest_lock     = __import__("threading").Lock()
        self._last_digest:    datetime  = datetime.now()'''

if old_init in src:
    src = src.replace(old_init, new_init, 1)
    print('FIX 1 OK: digest queue added to AlertSystem')
else:
    print('FIX 1 FAIL')

# ── Fix 2: Replace _email_alert with digest-aware version ────────────────────
old_email = '''    def _email_alert(self, signal: BreakoutSignal, message: str):
        sym  = signal.symbol
        last = self.email_last_sent.get(sym)
        if last and (datetime.now()-last).total_seconds() < 600: return
        try:
            ef = self.config.get("email_from",""); et = self.config.get("email_to","")
            pw = self.config.get("email_password","")
            if not all([ef, et, pw]): return
            subj = f"BREAKOUT: [{signal.broker}] {sym}"
            # MIME with UTF-8 so emojis in the body are handled correctly
            msg = MIMEMultipart()
            msg["From"]    = ef
            msg["To"]      = et
            msg["Subject"] = subj
            msg.attach(MIMEText(message, "plain", "utf-8"))
            with smtplib.SMTP(self.config.get("email_smtp_server","smtp.gmail.com"),
                              self.config.get("email_smtp_port",587)) as srv:
                srv.starttls()
                srv.login(ef, pw)
                srv.sendmail(ef, et, msg.as_bytes())
            self.email_last_sent[sym] = datetime.now()
        except Exception as e:
            logger.error(f"Email failed: {e}")'''

new_email = '''    def _email_alert(self, signal: BreakoutSignal, message: str,
                     escalation: int = 0):
        """
        Escalation 3 (ROCKET >10%): send immediately.
        All others: add to 2-hour digest queue.
        Per-symbol cooldown: 30 minutes.
        """
        sym  = signal.symbol
        last = self.email_last_sent.get(sym)
        if last and (datetime.now()-last).total_seconds() < 1800:
            return   # 30-min per-symbol cooldown

        ef = self.config.get("email_from","")
        et = self.config.get("email_to","")
        pw = self.config.get("email_password","")
        if not all([ef, et, pw]):
            return

        self.email_last_sent[sym] = datetime.now()

        if escalation >= 3:
            # ROCKET — send immediately
            self._send_email_now(
                ef, et, pw,
                subject=f"ROCKET ALERT: [{signal.broker}] {sym}",
                body=message
            )
        else:
            # Add to digest queue
            mpct = move_pct(signal.entry_price, signal.current_price)
            line = (f"[{signal.broker}] {sym:12s} "
                    f"{'+' if mpct>=0 else ''}{mpct:.2f}% "
                    f"@ ${signal.current_price:.4f} "
                    f"| esc={escalation}")
            with self._digest_lock:
                self._digest_queue.append(line)
            # Flush digest if 2 hours have passed
            self._maybe_flush_digest(ef, et, pw)

    def _maybe_flush_digest(self, ef: str, et: str, pw: str):
        DIGEST_INTERVAL_SECS = 2 * 3600   # 2 hours
        now = datetime.now()
        elapsed = (now - self._last_digest).total_seconds()
        with self._digest_lock:
            if elapsed < DIGEST_INTERVAL_SECS or not self._digest_queue:
                return
            lines = list(self._digest_queue)
            self._digest_queue.clear()
            self._last_digest = now
        count = len(lines)
        body  = (
            f"Breakout Scanner Digest — {now.strftime('%Y-%m-%d %H:%M PT')}\n"
            f"{count} signal(s) since last digest:\n\n"
            + "\n".join(lines)
            + "\n\nROCKET (>10%) alerts are sent immediately regardless of digest."
        )
        self._send_email_now(
            ef, et, pw,
            subject=f"Breakout Digest: {count} signals",
            body=body
        )

    def _send_email_now(self, ef: str, et: str, pw: str,
                        subject: str, body: str):
        try:
            msg = MIMEMultipart()
            msg["From"]    = ef
            msg["To"]      = et
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            with smtplib.SMTP(self.config.get("email_smtp_server", "smtp.gmail.com"),
                              self.config.get("email_smtp_port", 587)) as srv:
                srv.starttls()
                srv.login(ef, pw)
                srv.sendmail(ef, et, msg.as_bytes())
            logger.info(f"Email sent: {subject}")
        except Exception as e:
            logger.error(f"Email failed: {e}")'''

if old_email in src:
    src = src.replace(old_email, new_email, 1)
    print('FIX 2 OK: _email_alert now uses digest queue, rockets immediate')
else:
    print('FIX 2 FAIL')

# ── Fix 3: Pass escalation to _email_alert in send_alert ────────────────────
old_send = '''        if self.config.get("enable_email_alert", False):
            self._email_alert(signal, message)'''

new_send = '''        if self.config.get("enable_email_alert", False):
            self._email_alert(signal, message, escalation=escalation)'''

if old_send in src:
    src = src.replace(old_send, new_send, 1)
    print('FIX 3 OK: escalation passed to _email_alert')
else:
    print('FIX 3 FAIL')

with open('BreakoutScanner.py', 'w', encoding='utf-8') as f:
    f.write(src)

print('Done. Restart BreakoutScanner.')
print('Email rules:')
print('  ROCKET (>10%) -> immediate email')
print('  All others    -> 2-hour digest batch')
print('  Per-symbol cooldown: 30 minutes')
