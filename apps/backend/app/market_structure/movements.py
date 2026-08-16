"""
Pelabelan struktur wave di atas pivot hasil PivotDetector.

final.md §3.1 (5 wave turun, untuk Bullish Divergence):
    "Cari penurunan terpanjang ... biasanya ini adalah wave ke-3 ...
     Setelah wave-3 teridentifikasi, cek apakah sudah terbentuk 5 kali
     gerakan turun."
    Pola pivot yang dicari: Low(W1) - High(W2) - Low(W3) - High(W4) - Low(W5)

final.md §5.1 (pola konsolidasi A-B-C-D-E, untuk Hidden Bullish Divergence):
    "Minimal ada 5 gerakan di dalam pola konsolidasi ... A-B-C-D-E"
    Pola pivot yang dicari: Low(A) - High(B) - Low(C) - High(D) - [zona E]
"""

import pandas as pd
from typing import Dict, Optional


class MovementClassifier:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def classify_movements(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        """Menambah kolom `magnitude` (besar pergerakan antar pivot berurutan)."""
        if len(pivots_df) < 2:
            return pivots_df.copy()
        pivots = pivots_df.copy()
        pivots["magnitude"] = pivots["price"].diff().abs()
        return pivots

    def label_5_movements(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        """
        Melabeli struktur 5 wave turun paling BARU yang polanya cocok:
        Low-High-Low-High-Low (-1, 1, -1, 1, -1), dengan wave-3 = penurunan
        terpanjang di antara dua leg turun (W2->W3 dan W4->W5), sesuai
        final.md §3.1.
        """
        if len(pivots_df) < 5:
            return pivots_df.copy().assign(movement_label=None)

        pivots = pivots_df.copy()
        labels = [None] * len(pivots)

        for i in range(len(pivots) - 1, 3, -1):
            p5, p4, p3, p2, p1 = (pivots.iloc[i], pivots.iloc[i - 1], pivots.iloc[i - 2],
                                   pivots.iloc[i - 3], pivots.iloc[i - 4])

            if not (p5["type"] == -1 and p4["type"] == 1 and p3["type"] == -1
                    and p2["type"] == 1 and p1["type"] == -1):
                continue

            # Rule §3.1: wave-3 harus penurunan TERPANJANG di antara dua leg turun.
            drop_to_w3 = p2["price"] - p3["price"]   # leg turun W2 -> W3
            drop_to_w5 = p4["price"] - p5["price"]   # leg turun W4 -> W5

            if drop_to_w3 > 0 and drop_to_w3 > drop_to_w5:
                labels[i] = "W5"
                labels[i - 1] = "W4"
                labels[i - 2] = "W3"
                labels[i - 3] = "W2"
                labels[i - 4] = "W1"
                break  # ambil struktur 5-wave paling baru saja

        pivots["movement_label"] = labels
        return pivots

    def label_abcde(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        """
        Melabeli pola konsolidasi A-B-C-D-E paling baru (final.md §5.1):
        Low(A) - High(B) - Low(C) - High(D), lalu zona E dihitung terpisah
        oleh HiddenBullishDivergenceStrategy dari C->D (bukan pivot tersendiri,
        karena E adalah ZONA entry, bukan titik yang sudah terjadi).
        """
        if len(pivots_df) < 4:
            return pivots_df.copy().assign(abcde_label=None)

        pivots = pivots_df.copy()
        labels = [None] * len(pivots)

        for i in range(len(pivots) - 1, 2, -1):
            pD, pC, pB, pA = pivots.iloc[i], pivots.iloc[i - 1], pivots.iloc[i - 2], pivots.iloc[i - 3]

            # Wajib mulai dari LOW (A) -- final.md §5.1: pola konsolidasi
            # setelah kenaikan, A adalah low awal konsolidasi.
            if (pA["type"] == -1 and pB["type"] == 1 and pC["type"] == -1 and pD["type"] == 1
                    and pC["price"] > pA["price"]):  # harga higher-low (syarat hidden div, §5.1)
                labels[i] = "D"
                labels[i - 1] = "C"
                labels[i - 2] = "B"
                labels[i - 3] = "A"
                break

        pivots["abcde_label"] = labels
        return pivots
