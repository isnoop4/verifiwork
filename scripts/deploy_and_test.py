"""
Deploy + test alur penuh TranscriptionEscrow di Studio Next.

PERUBAHAN: read_contract() (gen_call) terbukti gagal konsisten dengan error
"Contract ... not found" di beberapa deploy berturut-turut, PADAHAL explorer
mengonfirmasi kontraknya benar-benar finalized. Ini kemungkinan bug di jalur
baca RPC gen_call untuk Studio Next di versi SDK ini -- bukan soal kontrak
kita. Jadi script ini TIDAK memanggil read_contract sama sekali. Verifikasi
status akhir dilakukan manual lewat explorer:
    https://explorer-studio-dev.genlayer.com/address/<CONTRACT_ADDRESS>

Jalankan:
    python scripts/deploy_and_test.py
"""

import os
import json
import pathlib

from genlayer_py import create_client, create_account
from genlayer_py.chains import studio_devnet


def load_private_key() -> str:
    env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("DEPLOYER_PRIVATE_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("DEPLOYER_PRIVATE_KEY")
    if not key:
        raise SystemExit("DEPLOYER_PRIVATE_KEY tidak ditemukan di .env maupun env var")
    return key


def get_fees(client):
    """Estimasi generik -- dipakai untuk deploy (belum ada equivalent
    estimate_transaction_fees_for_deploy() di SDK ini)."""
    estimate = client.estimate_transaction_fees(
        {
            "leaderTimeunitsAllocation": 100,
            "validatorTimeunitsAllocation": 200,
            "rotations": [0],
        }
    )
    return {"distribution": estimate["distribution"], "feeValue": estimate["feeValue"]}


def get_write_fees(client, account, address, function_name, args, value=0):
    """Estimasi khusus per-transaksi -- otomatis mendeteksi alokasi yang
    dibutuhkan TERMASUK pesan eksternal (mis. emit_transfer ke EOA di
    evaluate_and_release), yang tidak tercakup oleh estimasi generik di
    atas dan menyebabkan error 'fee no_matching_allocation # external'."""
    recommended = client.estimate_transaction_fees_for_write(
        account=account,
        address=address,
        function_name=function_name,
        args=args,
        value=value,
    )
    return {
        "distribution": recommended["distribution"],
        "feeValue": recommended["feeValue"],
    }


def wait_final(client, tx_hash, label):
    print(f"[{label}] menunggu finalisasi...")
    receipt = client.wait_for_transaction_receipt(
        transaction_hash=tx_hash,
        wait_until="finalized",
        retries=40,
    )
    lifecycle = receipt.get("lifecycle")
    outcome = lifecycle.get("outcome") if isinstance(lifecycle, dict) else None
    print(f"[{label}] lifecycle:", lifecycle, "| outcome:", outcome)
    return receipt


def main():
    private_key = load_private_key()
    account = create_account(account_private_key=private_key)
    client = create_client(chain=studio_devnet, account=account)

    contract_path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "contracts"
        / "transcription_escrow.py"
    )
    contract_code = contract_path.read_bytes()

    print("=== DEPLOY ===")
    fees = get_fees(client)
    tx_hash = client.deploy_contract(code=contract_code, args=[], fees=fees)
    receipt = wait_final(client, tx_hash, "deploy")

    contract_address = receipt.get("data", {}).get("contract_address")
    if not contract_address:
        print(json.dumps(receipt, indent=2, default=str))
        raise SystemExit("Contract address tidak ketemu di receipt -- cek struktur JSON di atas")
    print("Contract address:", contract_address)
    print("Explorer:", f"https://explorer-studio-dev.genlayer.com/address/{contract_address}")

    print("\n=== WRITE: create_task (value=1000) ===")
    fees = get_write_fees(
        client, account, contract_address, "create_task",
        ["https://example.com/audio.mp3", "rubric: transkrip harus akurat dan lengkap"],
        value=1000,
    )
    tx_hash = client.write_contract(
        account=account,
        address=contract_address,
        function_name="create_task",
        args=["https://example.com/audio.mp3", "rubric: transkrip harus akurat dan lengkap"],
        value=1000,
        fees=fees,
    )
    wait_final(client, tx_hash, "create_task")

    print("\n=== WRITE: submit_result ===")
    fees = get_write_fees(
        client, account, contract_address, "submit_result",
        ["Ini transkrip hasil kerja worker, akurat dan lengkap sesuai rubric."],
    )
    tx_hash = client.write_contract(
        account=account,
        address=contract_address,
        function_name="submit_result",
        args=["Ini transkrip hasil kerja worker, akurat dan lengkap sesuai rubric."],
        fees=fees,
    )
    wait_final(client, tx_hash, "submit_result")

    print("\n=== WRITE: evaluate_and_release (LLM sungguhan, bisa lama) ===")
    fees = get_write_fees(client, account, contract_address, "evaluate_and_release", [])
    tx_hash = client.write_contract(
        account=account,
        address=contract_address,
        function_name="evaluate_and_release",
        args=[],
        fees=fees,
    )
    receipt = wait_final(client, tx_hash, "evaluate_and_release")
    print(json.dumps(receipt, indent=2, default=str))

    print("\n=== SELESAI ===")
    print("Contract address:", contract_address)
    print("Cek status akhir & hasil verdict LLM di explorer:")
    print(f"  https://explorer-studio-dev.genlayer.com/address/{contract_address}")


if __name__ == "__main__":
    main()
