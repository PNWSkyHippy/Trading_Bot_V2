with open('config.py', encoding='utf-8') as f:
    src = f.read()

# Add CLAUDE_REVIEWER_ENABLED = False near the top after other config flags
old = '# ── Trading parameters\n'
new = '# ── Claude Reviewer\nCLAUDE_REVIEWER_ENABLED = False   # Set True to re-enable when budget allows\n\n# ── Trading parameters\n'

if 'CLAUDE_REVIEWER_ENABLED' not in src:
    if old in src:
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(src.replace(old, new, 1))
        print('Fix 1 OK: CLAUDE_REVIEWER_ENABLED = False added to config.py')
    else:
        # Just append it near the end of config constants
        # Find a safe insertion point
        marker = 'ANTHROPIC_API_KEY'
        idx = src.find(marker)
        if idx > 0:
            line_end = src.find('\n', idx)
            new_src = src[:line_end+1] + 'CLAUDE_REVIEWER_ENABLED = False   # Set True to re-enable\n' + src[line_end+1:]
            with open('config.py', 'w', encoding='utf-8') as f:
                f.write(new_src)
            print('Fix 1 OK: CLAUDE_REVIEWER_ENABLED = False added after ANTHROPIC_API_KEY')
        else:
            print('Fix 1 FAIL: could not find insertion point in config.py')
else:
    print('Fix 1 SKIP: CLAUDE_REVIEWER_ENABLED already in config.py')

# Fix 2: claude_reviewer.py - check the flag at startup
with open('intelligence/claude_reviewer.py', encoding='utf-8') as f:
    cr = f.read()

old2 = '''    def __init__(self):
        load_dotenv(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
        )
        self._api_key         = config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        self._morning_context: Optional[MarketContext] = None
        self._briefing_time:  Optional[datetime]       = None
        self.enabled          = bool(self._api_key)'''

new2 = '''    def __init__(self):
        load_dotenv(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
        )
        self._api_key         = config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        self._morning_context: Optional[MarketContext] = None
        self._briefing_time:  Optional[datetime]       = None
        # Check master enable flag — set CLAUDE_REVIEWER_ENABLED=False in config to
        # disable all API calls without removing the API key from .env
        reviewer_flag = getattr(config, "CLAUDE_REVIEWER_ENABLED", True)
        self.enabled  = bool(self._api_key) and reviewer_flag
        if not reviewer_flag:
            logger.info(
                "ClaudeReviewer: CLAUDE_REVIEWER_ENABLED=False in config — "
                "reviewer disabled. All signals proceed to execution without review."
            )'''

if old2 in cr:
    with open('intelligence/claude_reviewer.py', 'w', encoding='utf-8') as f:
        f.write(cr.replace(old2, new2, 1))
    print('Fix 2 OK: reviewer respects CLAUDE_REVIEWER_ENABLED flag')
else:
    print('Fix 2 FAIL')

# Fix 3: When reviewer is disabled, signals should APPROVE not SKIP
# The current SKIP fallback is too conservative when reviewer is intentionally off
old3 = '''        if not self.enabled:
            return SignalDecision(
                decision=SKIP, reasoning="Reviewer disabled",
                error=True, elapsed_ms=0
            )'''

new3 = '''        if not self.enabled:
            # Reviewer intentionally disabled — pass through to execution
            return SignalDecision(
                decision=APPROVE,
                reasoning="Reviewer disabled — signal passes through",
                confidence=50,
                error=False,
                elapsed_ms=0
            )'''

if old3 in cr:
    # Need to reload since we may have changed it above
    with open('intelligence/claude_reviewer.py', encoding='utf-8') as f:
        cr2 = f.read()
    if old3 in cr2:
        with open('intelligence/claude_reviewer.py', 'w', encoding='utf-8') as f:
            f.write(cr2.replace(old3, new3, 1))
        print('Fix 3 OK: disabled reviewer APPROVEs signals instead of SKIPping')
    else:
        print('Fix 3 SKIP: already applied in previous step')
else:
    print('Fix 3 FAIL')

print('Done. Restart bot. All signals will now execute without Haiku review.')
print('To re-enable: set CLAUDE_REVIEWER_ENABLED = True in config.py')
