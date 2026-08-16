import os
from typing import Optional
from groq import Groq
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.api_key = settings.GROQ_API
        if not self.api_key:
            print("WARNING: GROQ_API key is missing.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)

    async def generate_explanation(self, signal_data: dict, model: str = "llama-3.3-70b-versatile") -> str:
        """
        Generates reasoning and explanation for a signal according to final.md §0 & §5.
        Output is in Indonesian, plain text, no markdown symbols.
        """
        if not self.client:
            return "Layanan LLM belum dikonfigurasi."

        prompt = f"""
        Analisis sinyal trading berikut berdasarkan strategi Divergence Method (CTG):
        Data Sinyal: {signal_data}

        Berikan penjelasan mendalam mengapa emiten ini lolos filter, pola divergence yang terdeteksi, dan target levelnya.

        PENTING:
        1. Pastikan menyebutkan rencana entri pada {signal_data.get('prediksi_entri')} ({signal_data.get('keterangan_waktu')}).
        2. Jika hari tersebut adalah hari libur nasional (seperti 17 Agustus), pastikan penjelasan Anda mencerminkan bahwa pasar tutup dan entri dilakukan pada hari bursa berikutnya yang tersedia.
        3. Konfirmasi bahwa TP ({signal_data.get('tp')}) harus lebih tinggi dari Entry ({signal_data.get('entry')}) untuk posisi Long.

        ATURAN OUTPUT:
        1. Gunakan Bahasa Indonesia yang profesional.
        2. Tuliskan dalam bentuk paragraf teks lengkap (Full Text).
        3. DILARANG menggunakan simbol format seperti bintang double (**), pagar (#), atau list (-).
        4. Jangan gunakan penebalan teks (bold) atau miring (italic).
        5. Fokus pada alasan logis sesuai instruksi strategi CTG.
        """

        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Anda adalah pakar analis trading saham yang mahir dalam Metode Divergence (CTG). Anda selalu menjawab dengan teks polos Bahasa Indonesia tanpa simbol markdown."},
                    {"role": "user", "content": prompt}
                ]
            )
            content = completion.choices[0].message.content

            # Post-processing to strip any remaining markdown symbols just in case
            clean_text = content.replace("**", "").replace("__", "").replace("#", "").replace("*", "")
            return clean_text.strip()
        except Exception as e:
            return f"Gagal menghasilkan analisis: {e}"

llm_service = LLMService()
