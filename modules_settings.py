import asyncio
from modules import *


async def daily_hit(account_id, key):
    nfprompt = NfPrompt(account_id, key, "opbnb")
    await nfprompt.hit()


def get_tx_count():
    asyncio.run(check_tx())
