import json

with open('data/rpc.json') as file:
    RPC = json.load(file)

with open("accounts.txt", "r") as file:
    ACCOUNTS = [row.strip() for row in file]
