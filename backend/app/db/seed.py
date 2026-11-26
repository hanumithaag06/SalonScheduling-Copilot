# Why: Entrypoint proxy for database seeding so that both
# `python seed.py` and `python -m app.db.seed` work seamlessly.

import asyncio
import os
import sys

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from seed import main, seed_data

if __name__ == "__main__":
    asyncio.run(main())
