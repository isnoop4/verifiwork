"""
Test alur penuh TranscriptionEscrow yang sudah dideploy ke Studio Next.

Jalankan:
    python scripts/interact.py

Butuh DEPLOYER_PRIVATE_KEY di .env (akun yang sama dipakai buat deploy,
sekaligus jadi "requester" di alur ini).
"""

import os
import pathlib
import json
import time

from genlayer_py import create_client, create_account
from genlayer_py.chains import studio_devnet


CONTRACT_ADDRESS = "0x2F1c58bBeeafF4dF8543CB6299B7247f960ab2cE"


def load_private_key() -> str:
    env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("DEPLOYER_PRIVATE_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("DEPLOYER_PRIVATE_KEY")
    if not key:
        raise SystemExit("DEPLOYER_PRIVATE_KEY tidak ditemukan")
    return key


def get_fees(client):
    estimate = client.estimate_transaction_fees(
        {
            "leaderTimeunitsAllocation": 100,
            "validatorTimeunitsAllocation": 200,
            "rotations": [0],
        }
    )
    return {
        "distribution": estimate["distribution"],
        "feeValue": estimate["feeValue"],
    }


def main():
    private_key = load_private_key()
    account = create_account(account_private_key=private_key)
    client = create_client(chain=studio_devnet, account=account)

    print("=== Status awal ===")
    status = client.read_contract(
        address=CONTRACT_ADDRESS,
        function_name="get_status",
        args=[],
    )
    print("status:", status)

    print("\n=== create_task (kirim 1000 wei sebagai reward) ===")
    fees = get_fees(client)
    tx_hash = client.write_contract(
        account=account,
        address=CONTRACT_ADDRESS,
        function_name="create_task",
        args=["https://example.com/audio.mp3", "rubric: transkrip harus akurat dan lengkap"],
        value=1000,
        fees=fees,
    )
    print("tx_hash:", tx_hash)
    receipt = client.wait_for_transaction_receipt(transaction_hash=tx_hash, wait_until="finalized", retries=40)
    print("lifecycle:", receipt.get("lifecycle") or receipt.get("data", {}).get("lifecycle"))

    status = client.read_contract(address=CONTRACT_ADDRESS, function_name="get_status", args=[])
    print("status setelah create_task:", status)

    print("\n=== submit_result (worker = akun yang sama untuk sekarang) ===")
    fees = get_fees(client)
    tx_hash = client.write_contract(
        account=account,
        address=CONTRACT_ADDRESS,
        function_name="submit_result",
        args=["Ini transkrip hasil kerja worker, akurat dan lengkap sesuai rubric."],
        fees=fees,
    )
    print("tx_hash:", tx_hash)
    receipt = client.wait_for_transaction_receipt(transaction_hash=tx_hash, wait_until="finalized", retries=40)
    print("lifecycle:", receipt.get("lifecycle") or receipt.get("data", {}).get("lifecycle"))

    status = client.read_contract(address=CONTRACT_ADDRESS, function_name="get_status", args=[])
    print("status setelah submit_result:", status)

    print("\n=== evaluate_and_release (panggil LLM sungguhan, bisa 60-90 detik) ===")
    fees = get_fees(client)
    tx_hash = client.write_contract(
        account=account,
        address=CONTRACT_ADDRESS,
        function_name="evaluate_and_release",
        args=[],
        fees=fees,
    )
    print("tx_hash:", tx_hash)
    receipt = client.wait_for_transaction_receipt(transaction_hash=tx_hash, wait_until="finalized", retries=40)
    print(json.dumps(receipt, indent=2, default=str))

    status = client.read_contract(address=CONTRACT_ADDRESS, function_name="get_status", args=[])
    reason = client.read_contract(address=CONTRACT_ADDRESS, function_name="get_verdict_reason", args=[])
    print("\n=== HASIL AKHIR ===")
    print("status:", status)
    print("verdict_reason:", reason)


if __name__ == "__main__":
    main()
