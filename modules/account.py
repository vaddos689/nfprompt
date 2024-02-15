import asyncio
import time
import random
from typing import Union, Type, Dict, Any

from hexbytes import HexBytes
from loguru import logger
from web3 import AsyncWeb3
from eth_account import Account as EthereumAccount
from web3.contract import Contract
from web3.exceptions import TransactionNotFound
from web3.middleware import async_geth_poa_middleware

from config import RPC
from settings import MAX_PRIORITY_FEE
from utils.sleeping import sleep


class Account:
    def __init__(self, account_id: int, private_key: str, chain: str) -> None:
        self.account_id = account_id
        self.private_key = private_key
        self.chain = chain
        self.explorer = RPC[chain]["explorer"]
        self.token = RPC[chain]["token"]

        self.w3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(random.choice(RPC[chain]["rpc"])),
            middlewares=[async_geth_poa_middleware],
            request_kwargs={'verify': False}
        )

        self.account = EthereumAccount.from_key(private_key)
        self.address = self.account.address

    async def get_tx_data(self, value: int = 0, gas_price: bool = True):
        tx = {
            "chainId": await self.w3.eth.chain_id,
            "from": self.address,
            "value": value,
            "nonce": await self.w3.eth.get_transaction_count(self.address),
        }

        if gas_price:
            tx.update({"gasPrice": await self.w3.eth.gas_price})

        return tx

    async def get_balance(self, contract_address: str) -> Dict:
        contract_address = self.w3.to_checksum_address(contract_address)
        contract = self.get_contract(contract_address)

        symbol = await contract.functions.symbol().call()
        decimal = await contract.functions.decimals().call()
        balance_wei = await contract.functions.balanceOf(self.address).call()

        balance = balance_wei / 10 ** decimal

        return {"balance_wei": balance_wei, "balance": balance, "symbol": symbol, "decimal": decimal}

    async def wait_until_tx_finished(self, hash: str, max_wait_time=180) -> None:
        start_time = time.time()
        while True:
            try:
                receipts = await self.w3.eth.get_transaction_receipt(hash)
                status = receipts.get("status")
                if status == 1:
                    logger.success(f"[{self.account_id}][{self.address}] {self.explorer}{hash} successfully!")
                    return
                elif status is None:
                    await asyncio.sleep(0.3)
                else:
                    logger.error(f"[{self.account_id}][{self.address}] {self.explorer}{hash} transaction failed!")
                    return
            except TransactionNotFound:
                if time.time() - start_time > max_wait_time:
                    print(f'FAILED TX: {hash}')
                    return
                await asyncio.sleep(1)

    async def sign(self, transaction) -> Any:
        if transaction.get("gasPrice", None) is None:
            max_priority_fee_per_gas = self.w3.to_wei(MAX_PRIORITY_FEE["opbnb"], "gwei")
            max_fee_per_gas = await self.w3.eth.gas_price

            transaction.update(
                {
                    "maxPriorityFeePerGas": max_priority_fee_per_gas,
                    "maxFeePerGas": max_fee_per_gas,
                }
            )

        gas = await self.w3.eth.estimate_gas(transaction)
        gas = int(gas * 1)

        transaction.update({"gas": gas})

        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)

        return signed_txn

    async def send_raw_transaction(self, signed_txn) -> HexBytes:
        txn_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return txn_hash