# VerifiWork

> Marketplace micro-task (dimulai dari transkripsi audio) di mana kualitas hasil kerja dinilai oleh AI validator terhadap rubrik publik, dan pembayaran cair otomatis dari escrow — dibangun untuk **GenLayer Agent Tank**, track **Future of Work**.

## Masalah

Pekerja platform gig data-work (transkripsi, evaluasi AI, anotasi) menghadapi:
- Penilaian kualitas subjektif dari satu reviewer
- Sengketa pembayaran yang lambat dan tidak transparan
- Reputasi yang terkunci di satu platform

## Solusi

Intelligent Contract di GenLayer yang menjalankan siklus kerja end-to-end:

1. **Requester** posting task + rubrik kualitas publik + reward (native GEN), dana masuk escrow on-chain
2. **Worker** submit hasil kerja
3. **Validator committee AI** (via GenLayer Equivalence Principle) menilai hasil terhadap rubrik yang didefinisikan di kode kontrak
4. Jika **APPROVED** → reward cair otomatis ke worker
5. Jika **REJECTED** → dana refund otomatis ke requester

## Status

✅ Contract `TranscriptionEscrow` sudah dites end-to-end di GenLayer Studio:
- `create_task` → `submit_result` → `evaluate_and_release`
- Kedua skenario terverifikasi: REJECTED (transkrip buruk, refund ke requester) dan APPROVED (transkrip baik, payout ke worker)

## Arsitektur Teknis

Lihat [`contracts/transcription_escrow.py`](contracts/transcription_escrow.py).

**State utama:** `requester`, `worker`, `reward`, `audio_url`, `rubric`, `transcript`, `status`, `verdict_reason`

**Fungsi:**
| Fungsi | Tipe | Deskripsi |
|---|---|---|
| `create_task(audio_url, rubric)` | write, payable | Requester membuat task, kirim reward via `gl.message.value` |
| `submit_result(transcript_text)` | write | Worker submit hasil kerja |
| `evaluate_and_release()` | write | AI validator menilai transkrip vs rubric (`gl.eq_principle.prompt_non_comparative`), lalu auto payout/refund via `gl.get_contract_at().emit_transfer()` |
| `dispute()` | write | Placeholder banding (belum full diimplementasi) |
| `get_status()`, `get_reward()`, `get_verdict_reason()`, `get_task_details()` | view | Baca status task |

**Mitigasi risiko:**
- Input worker dibungkus sebagai `DATA_ONLY_NOT_INSTRUCTIONS` di prompt evaluasi untuk mitigasi prompt injection
- Output evaluasi diekstrak sebagai JSON dari raw output (robust terhadap model yang menyertakan reasoning/`<think>` block sebelum JSON)
- Rubric hanya berisi kriteria yang bisa diverifikasi dari teks transkrip (bukan perbandingan langsung ke audio asli)

## Cara Coba

1. Deploy `contracts/transcription_escrow.py` di [GenLayer Studio](https://studio.genlayer.com)
2. Panggil `create_task` dengan `audio_url`, `rubric`, dan kirim value GEN sebagai reward
3. Panggil `submit_result` dengan teks transkrip
4. Panggil `evaluate_and_release` — validator AI akan menilai dan mencairkan dana otomatis
5. Cek `get_status()` dan `get_verdict_reason()` untuk melihat hasil

## Keterbatasan (MVP)

- Baru mendukung 1 task aktif per contract instance (belum multi-task)
- `dispute()` masih placeholder, belum trigger re-evaluasi committee lebih besar
- Rubric belum bisa memverifikasi kesesuaian transkrip terhadap audio asli (validator hanya menerima teks)
- Belum ada reputation tracker terpisah (rencana pengembangan lanjutan)

## Rencana Pengembangan Lanjutan

- Contract `ReputationTracker` terpisah untuk skor historis worker (portable ke platform lain)
- Multi-task per contract (task registry)
- Appeal path penuh dengan committee lebih besar

## Track

Future of Work — GenLayer Agent Tank
