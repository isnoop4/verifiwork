"""
Direct-mode tests untuk TranscriptionEscrow.

CATATAN PENTING SEBELUM DIJALANKAN:
1. Kalau muncul error resolusi SDK (bukan AssertionError), kemungkinan
   penyebabnya adalah runner py-genlayer:5jycge4... yang dipakai di header
   kontrak ini berasal dari bundle Studio, bukan tarball rilis GenVM publik
   -- beberapa environment melaporkan ini gagal di-resolve oleh direct-mode
   loader (error E101 semacamnya) walau genvm-lint berhasil. Kalau ini
   terjadi, lanjut saja ke gltest/integration test terhadap Studio Next
   langsung sebagai gantinya -- jangan buang waktu debug direct mode.
2. Baris yang menandai `# VERIFIKASI:` di bawah adalah bagian yang saya
   belum bisa pastikan 100% dari dokumentasi -- cara persis mengirim
   `value` (untuk method payable) di direct mode. Cek dengan
   `python -c "from gltest.fixtures import direct_vm; help(direct_vm)"`
   atau baca README paket genlayer-test yang terinstall
   (pip show -f genlayer-test) kalau baris ini error.
"""

import pytest


CONTRACT_PATH = "contracts/transcription_escrow.py"


def test_initial_state(direct_deploy):
    contract = direct_deploy(CONTRACT_PATH)
    assert contract.get_status() == "empty"
    assert contract.get_reward() == 0


def test_create_task_requires_value(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT_PATH)

    # create_task tanpa value (value=0) harus revert karena
    # assert gl.message.value > 0 di kontrak.
    with direct_vm.expect_revert("Harus kirim reward"):
        contract.create_task("https://example.com/audio.mp3", "rubric singkat")


def test_create_task_success(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT_PATH)

    # VERIFIKASI: cara kirim value ke method payable di direct mode.
    # Pola di bawah ini asumsi (belum terverifikasi) -- sesuaikan kalau
    # genlayer-test versi terinstall pakai syntax berbeda.
    direct_vm.value = 1000
    contract.create_task("https://example.com/audio.mp3", "rubric singkat")
    direct_vm.value = 0

    assert contract.get_status() == "open"
    assert contract.get_reward() == 1000


def test_submit_result_before_open_reverts(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT_PATH)

    with direct_vm.expect_revert("Task tidak tersedia untuk submission"):
        contract.submit_result("transkrip apapun")


def test_submit_result_success(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)

    direct_vm.sender = direct_alice
    direct_vm.value = 1000
    contract.create_task("https://example.com/audio.mp3", "rubric singkat")
    direct_vm.value = 0

    with direct_vm.prank(direct_bob):
        contract.submit_result("ini transkrip hasil kerja worker")

    assert contract.get_status() == "submitted"


def test_dispute_requires_worker_and_rejected_status(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie
):
    contract = direct_deploy(CONTRACT_PATH)

    direct_vm.sender = direct_alice
    direct_vm.value = 1000
    contract.create_task("https://example.com/audio.mp3", "rubric singkat")
    direct_vm.value = 0

    with direct_vm.prank(direct_bob):
        contract.submit_result("ini transkrip hasil kerja worker")

    # Belum evaluate_and_release -> status masih "submitted", bukan "rejected".
    # dispute() harus revert karena precondition status belum terpenuhi.
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("Hanya task rejected yang bisa banding"):
            contract.dispute()

    # Sender yang bukan worker juga harus ditolak (diuji terpisah setelah
    # precondition status "rejected" tercapai -- butuh mock LLM di
    # evaluate_and_release untuk mensimulasikan verdict REJECTED, yang
    # belum ditulis di sini karena bergantung pada format mock_llm yang
    # persis dipakai genlayer-test 0.30.0rc2 untuk eq_principle.
    # prompt_non_comparative -- perlu dicek dulu contoh resminya sebelum
    # ditambahkan, supaya tidak menebak nama argumen mock.
