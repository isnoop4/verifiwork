"""
Deploy TranscriptionEscrow ke Studio Next pakai genlayer-py langsung
(BUKAN lewat gltest -- gltest 0.30.0rc2 belum handle fee flow v0.6).

Jalankan:
    python scripts/deploy.py

Butuh env var DEPLOYER_PRIVATE_KEY (baca dari .env manual di bawah,
supaya tidak perlu install python-dotenv tambahan kalau belum ada).

CATATAN JUJUR -- bagian yang saya tandai ASUMSI di bawah belum saya
konfirmasi 100% dari dokumentasi resmi. Kalau baris itu error, kirim
traceback-nya, saya perbaiki nama parameter/fungsinya.
"""

import os
import json
import pathlib

from genlayer_py import create_client, create_account

# ASUMSI: nama chain untuk Studio Next di genlayer-py adalah `studio_devnet`
# (konsisten dengan nama network di gltest.config.yaml kita). Kalau import
# ini gagal, coba `from genlayer_py import chains` lalu `dir(chains)` untuk
# lihat nama yang benar-benar tersedia.
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


def main():
    private_key = load_private_key()

    # Parameter yang benar: account_private_key (dikonfirmasi via
    # inspect.signature di HP kamu), bukan private_key.
    account = create_account(account_private_key=private_key)

    client = create_client(chain=studio_devnet, account=account)

    contract_path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "contracts"
        / "transcription_escrow.py"
    )
    contract_code = contract_path.read_bytes()

    print("Estimasi fee untuk deploy...")
    # ASUMSI: deploy di-price pakai estimator generik yang sama dengan write
    # (bukan fungsi estimate_transaction_fees_for_deploy() khusus -- itu
    # tidak ada di SDK ini per temuan riset).
    fee_estimate = client.estimate_transaction_fees(
        {
            "leaderTimeunitsAllocation": 100,
            "validatorTimeunitsAllocation": 200,
            "rotations": [0],
        }
    )
    print("Fee estimate:", fee_estimate)

    print("Deploying TranscriptionEscrow...")
    tx_hash = client.deploy_contract(
        code=contract_code,
        args=[],
        fees={
            "distribution": fee_estimate["distribution"],
            "feeValue": fee_estimate["feeValue"],
        },
    )
    print("Deploy tx hash:", tx_hash)

    print("Menunggu finalisasi (bisa 60-90 detik)...")
    receipt = client.wait_for_transaction_receipt(
        transaction_hash=tx_hash,
        wait_until="finalized",
        retries=40,
    )

    print(json.dumps(receipt, indent=2, default=str))

    # ASUMSI: alamat kontrak ada di salah satu field ini tergantung versi
    # (v0.6 katanya di txDataDecoded.contractAddress, versi lama di
    # data.contract_address). Cetak semua yang mungkin biar kelihatan.
    print("Kemungkinan contract address:")
    print(" - receipt.get('data', {}).get('contract_address'):",
          receipt.get("data", {}).get("contract_address") if isinstance(receipt.get("data"), dict) else None)
    print(" - receipt.get('txDataDecoded', {}).get('contractAddress'):",
          receipt.get("txDataDecoded", {}).get("contractAddress") if isinstance(receipt.get("txDataDecoded"), dict) else None)


if __name__ == "__main__":
    main()
