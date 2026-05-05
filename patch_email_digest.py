with open('BreakoutScanner.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: Add digest queue and error_email method to AlertSystem.__init__
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
        import threading as _thr
        self._digest_lock  = _thr.Lock()
        self._last_digest  = datetime.now()'''

if old_init in src:
    src = src.replace(old_init, new_init, 1)
    print('FIX 1 OK: digest vars added')
else:
    print('FIX 1 FAIL')

# Fix 2: Replace _email_alert — only fires on ROCKET (esc>=3), silent otherwise
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
        Email rules:
          ROCKET (escalation 3, >10% move) -> immediate email
          All others (watchlist, new alert, moving, hot) -> NO email
          Serious errors -> use send_error_email() directly
        Per-symbol cooldown: 30 minutes on rockets.
        """
        if escalation < 3:
            return   # only email on rockets and errors

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
        mpct = move_pct(signal.entry_price, signal.current_price)
        self._send_email_now(
            ef, et, pw,
            subject=f"ROCKET {mpct:+.1f}%: [{signal.broker}] {sym}",
            body=message
        )

    def send_error_email(self, subject: str, body: str):
        """Send an immediate email for serious errors (exchange down, etc.)."""
        ef = self.config.get("email_from","")
        et = self.config.get("email_to","")
        pw = self.config.get("email_password","")
        if not all([ef, et, pw]):
            return
        self._send_email_now(ef, et, pw, subject=f"[SCANNER ERROR] {subject}", body=body)

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
    print('FIX 2 OK: email only fires on ROCKET or explicit error')
else:
    print('FIX 2 FAIL')

# Fix 3: Pass escalation to _email_alert in send_alert
old_send = '''        if self.config.get("enable_email_alert", False):
            self._email_alert(signal, message)'''

new_send = '''        if self.config.get("enable_email_alert", False):
            self._email_alert(signal, message, escalation=escalation)'''

if old_send in src:
    src = src.replace(old_send, new_send, 1)
    print('FIX 3 OK: escalation passed through')
else:
    print('FIX 3 FAIL')

with open('BreakoutScanner.py', 'w', encoding='utf-8') as f:
    f.write(src)

print('Done. Restart BreakoutScanner.')
print('Email rules:')
print('  Watchlist / new signal / moving / hot -> NO email')
print('  ROCKET (>10%)                         -> immediate email')
print('  Serious errors                        -> immediate via send_error_email()')
