"""Print full stock + crypto watchlist as comma-separated lists for optimizer input."""
import os

ROOT = os.path.join(os.path.dirname(__file__), '..')

def load(path):
    syms = []
    try:
        with open(os.path.join(ROOT, path)) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    syms.append(line)
    except FileNotFoundError:
        pass
    return syms

stocks = load('watchlists/stocks.txt')
crypto = load('watchlists/crypto.txt')

print(f"\n=== STOCKS ({len(stocks)}) ===")
print(', '.join(stocks))
print(f"\n=== CRYPTO ({len(crypto)}) ===")
print(', '.join(crypto))
print(f"\n=== COMBINED ({len(stocks)+len(crypto)}) ===")
print(', '.join(stocks + crypto))
