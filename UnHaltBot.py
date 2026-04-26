from data.database import db; from datetime import date; db.update_session(date.today().isoformat(), trading_halted=0, halt_reason=None, consecutive_losses=0); print('Halt cleared')
