
from web3 import Web3
from web3.exceptions import TransactionNotFound
import json
import time

RPC_URL = "https://base.drpc.org"
NFT_CONTRACT_RAW = "0x1e71ea45fb939c92045ff32239a8922395eeb31b"
NFT_TOKEN_IDS = [2687, 775]
CHAIN_ID = 8453

with open("wallet.txt") as f:
    PRIVATE_KEYS = [line.strip() for line in f if line.strip()]

web3 = Web3(Web3.HTTPProvider(RPC_URL))
NFT_CONTRACT_ADDRESS = Web3.to_checksum_address(NFT_CONTRACT_RAW)

with open("nft_abi.json") as f:
    nft_abi = json.load(f)
nft_contract = web3.eth.contract(address=NFT_CONTRACT_ADDRESS, abi=nft_abi)

print("Загружены кошельки:")
for key in PRIVATE_KEYS:
    acct = web3.eth.account.from_key(key)
    print(f" - {acct.address}")

def wait_for_receipt(tx_hash, max_attempts=20):
    attempts = 0
    while attempts < max_attempts:
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            if receipt and receipt['status'] == 1:
                return True
            elif receipt and receipt['status'] == 0:
                return False
        except TransactionNotFound:
            pass
        time.sleep(5)
        attempts += 1
    print(f"Транзакция {tx_hash.hex()} не найдена в сети после ожидания.")
    return False

def send_nft(private_key, from_address, to_address, token_id):
    nonce = web3.eth.get_transaction_count(from_address)
    txn = nft_contract.functions.safeTransferFrom(from_address, to_address, token_id).build_transaction({
        'from': from_address,
        'gas': 200000,
        'gasPrice': web3.to_wei('0.0055', 'gwei'),
        'nonce': nonce,
        'chainId': CHAIN_ID
    })
    signed_txn = web3.eth.account.sign_transaction(txn, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Отправка NFT {token_id} от {from_address} к {to_address}: {tx_hash.hex()}")
    return tx_hash

def send_eth(private_key, from_address, to_address):
    balance = web3.eth.get_balance(from_address)
    gas_price = web3.to_wei('5', 'gwei')
    gas_limit = 21000
    max_fee = gas_price * gas_limit
    amount = balance - max_fee
    amount = int(amount * 0.99)
    if amount <= 0:
        print(f"Недостаточно ETH на {from_address} для перевода.")
        return
    nonce = web3.eth.get_transaction_count(from_address)
    tx = {
        'to': to_address,
        'value': amount,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': CHAIN_ID
    }
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Отправлено {web3.from_wei(amount, 'ether')} ETH с {from_address} на {to_address}: {tx_hash.hex()}")

if __name__ == "__main__":
    while len(PRIVATE_KEYS) >= 4:
        sender_1_key = PRIVATE_KEYS.pop(0)
        sender_2_key = PRIVATE_KEYS.pop(0)
        sender_1 = web3.eth.account.from_key(sender_1_key).address
        sender_2 = web3.eth.account.from_key(sender_2_key).address
        receiver_1 = web3.eth.account.from_key(PRIVATE_KEYS[0]).address
        receiver_2 = web3.eth.account.from_key(PRIVATE_KEYS[1]).address
        tx1 = send_nft(sender_1_key, sender_1, sender_2, NFT_TOKEN_IDS[0])
        tx2 = send_nft(sender_2_key, sender_2, sender_1, NFT_TOKEN_IDS[1])
        if wait_for_receipt(tx1) and wait_for_receipt(tx2):
            tx3 = send_nft(sender_2_key, sender_2, receiver_1, NFT_TOKEN_IDS[0])
            tx4 = send_nft(sender_1_key, sender_1, receiver_2, NFT_TOKEN_IDS[1])
            if wait_for_receipt(tx3) and wait_for_receipt(tx4):
                send_eth(sender_1_key, sender_1, receiver_2)
                send_eth(sender_2_key, sender_2, receiver_1)
            else:
                print("NFT не дошли до новых кошельков, ETH не отправлен.")
        else:
            print("NFT swap не удался, ETH не отправлен.")
        time.sleep(10)
    print("Все NFT и ETH успешно обработаны.")
