from loguru import logger
from web3 import Web3
from utils.helpers import retry
from .account import Account


class NfPrompt(Account):
    def __init__(self, account_id: int, private_key: str, chain: str) -> None:
        super().__init__(account_id=account_id, private_key=private_key, chain=chain)

    @retry
    async def hit(self):
        logger.info(f"[{self.account_id}][{self.address}] Daily HIT")

        tx_data = await self.get_tx_data(Web3.to_wei(0.0001, 'ether'))
        tx_data.update({"to": self.w3.to_checksum_address('0x3c76649cbae809e18bb577a9e291935f81a00195'),
                        "data": "0x2ae3594a"})

        signed_txn = await self.sign(tx_data)

        txn_hash = await self.send_raw_transaction(signed_txn)

        await self.wait_until_tx_finished(txn_hash.hex())
