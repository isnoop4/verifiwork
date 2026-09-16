"""
Integration test untuk TranscriptionEscrow di Studio Next (studio_devnet).

Jalankan dengan:
    gltest tests/integration/test_transcription_escrow_integration.py --network studio_devnet -v -s

Butuh:
- .env berisi DEPLOYER_PRIVATE_KEY (akun yang sudah ada test GEN di Studio Next)
- gltest.config.yaml sudah mengarah ke studio_devnet

CATATAN:
- Ini pakai Studio Mode API (get_contract_factory, .transact()/.call()),
  BEDA dari Direct Mode (tests/direct/) yang panggil method langsung.
- Test evaluate_and_release() memakai LLM sungguhan (bukan mock -- mock_llm
  cuma didukung di localnet), jadi hasil verdict-nya tidak 100% deterministik.
  Test ini hanya mengecek bahwa transaksinya SUKSES dieksekusi (tidak revert)
  dan status berpindah ke salah satu status terminal yang valah
  ("approved" atau "rejected") -- bukan mengecek verdict spesifik mana yang
  keluar, karena itu tergantung keputusan LLM validator sungguhan.
"""

import pytest

from gltest import get_contract_factory, get_default_account, create_account
from gltest.assertions import tx_execution_succeeded


CONTRACT_NAME = "TranscriptionEscrow"


@pytest.fixture
def deployed_contract():
    factory = get_contract_factory(CONTRACT_NAME)
    contract = factory.deploy(account=get_default_account())
    return contract


def test_initial_state_on_studio_next(deployed_contract):
    status = deployed_contract.get_status().call()
    assert status == "empty"


def test_create_task_flow_on_studio_next(deployed_contract):
    # NOTE: cara kirim `value` (native GEN) bareng .transact() di Studio Mode
    # belum saya konfirmasi 100% syntax-nya (apakah .transact(value=...) atau
    # parameter lain) -- kalau baris ini error soal keyword argument, kirim
    # traceback-nya, saya perbaiki.
    tx_receipt = deployed_contract.create_task(
        args=["https://example.com/audio.mp3", "rubric singkat"]
    ).transact(value=1000)

    assert tx_execution_succeeded(tx_receipt)

    status = deployed_contract.get_status().call()
    assert status == "open"

    reward = deployed_contract.get_reward().call()
    assert int(reward) == 1000


def test_full_flow_reaches_terminal_status_on_studio_next(deployed_contract):
    worker_account = create_account()

    tx1 = deployed_contract.create_task(
        args=["https://example.com/audio.mp3", "rubric singkat: transkrip harus akurat"]
    ).transact(value=1000)
    assert tx_execution_succeeded(tx1)

    tx2 = deployed_contract.submit_result(
        args=["Ini transkrip hasil kerja worker, cukup akurat dan lengkap."]
    ).transact(account=worker_account)
    assert tx_execution_succeeded(tx2)

    assert deployed_contract.get_status().call() == "submitted"

    tx3 = deployed_contract.evaluate_and_release().transact()
    assert tx_execution_succeeded(tx3)

    final_status = deployed_contract.get_status().call()
    assert final_status in ("approved", "rejected")
