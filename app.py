import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from io import BytesIO

import plotly.express as px

from googlenewsdecoder import new_decoderv1
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


# ==========================
# CONFIG
# ==========================

st.set_page_config(
    page_title="Berita Tidore AI",
    layout="wide"
)

st.title("📰 Dashboard Berita Tidore Kepulauan + AI")


# ==========================
# QUERY DEFAULT
# ==========================

default_queries = [
    "Tidore Kepulauan",
    "Kota Tidore Kepulauan",
    "Pemkot Tidore Kepulauan",
    "Wali Kota Tidore Kepulauan",
    "DPRD Tidore Kepulauan",
    "BPS Kota Tidore Kepulauan",
    "Maluku Utara Tidore",
    "Pulau Tidore",
    "Tidore Kepulauan ekonomi",
    "Tidore Kepulauan pembangunan",
    "Tidore Kepulauan kesehatan",
    "Tidore Kepulauan pendidikan",
    "Tidore Kepulauan pariwisata"
]


# ==========================
# SIDEBAR
# ==========================

st.sidebar.header("⚙️ Pengaturan")

tahun = st.sidebar.selectbox(
    "Tahun berita",
    [2024, 2025, 2026],
    index=2
)

start_month = st.sidebar.selectbox(
    "Bulan mulai",
    range(1, 13),
    index=2
)

end_month = st.sidebar.selectbox(
    "Bulan akhir",
    range(1, 13),
    index=4
)

jumlah = st.sidebar.number_input(
    "Jumlah berita",
    min_value=1,
    max_value=100,
    value=10
)


# ==========================
# QUERY PILIHAN
# ==========================

st.sidebar.subheader("🧾 Query Default")

selected_default = st.sidebar.multiselect(
    "Pilih query default",
    default_queries,
    default=default_queries
)

tambahan_query = st.sidebar.text_area(
    "Tambah query (pisahkan koma)",
    ""
)

queries = selected_default.copy()

if tambahan_query:
    queries.extend(
        [x.strip() for x in tambahan_query.split(",") if x.strip()]
    )


# ==========================
# KATEGORI RINGKASAN
# ==========================

st.sidebar.subheader("🤖 Kategori Ringkasan")

kategori_pilih = st.sidebar.multiselect(
    "Pilih kategori untuk diringkas",
    [
        "Pertanian/Primer",
        "Manufaktur/Sekunder",
        "Jasa/Tersier",
        "Tidak Teridentifikasi"
    ],
    default=["Jasa/Tersier"]
)


# ==========================
# AMBIL BERITA
# ==========================

def ambil_berita(queries, start, end, year, limit):

    data = []

    for query in queries:

        url = (
            "https://news.google.com/rss/search?q="
            + quote(query)
            + "&hl=id&gl=ID&ceid=ID:id"
        )

        feed = feedparser.parse(url)

        for berita in feed.entries:

            tanggal = berita.published_parsed

            if tanggal:

                tgl = datetime(
                    tanggal.tm_year,
                    tanggal.tm_mon,
                    tanggal.tm_mday
                )

                if (
                    tgl.year == year
                    and start <= tgl.month <= end
                ):

                    data.append({
                        "query": query,
                        "tanggal_terbit": tgl.strftime("%d-%m-%Y"),
                        "judul": berita.title,
                        "sumber": berita.source.title if "source" in berita else "",
                        "link": berita.link
                    })

    df = pd.DataFrame(data)

    if len(df) > 0:
        df = df.drop_duplicates(subset="judul")
        df = df.head(limit)

    return df


# ==========================
# DECODE LINK
# ==========================

def decode_google_news(url):
    try:
        hasil = new_decoderv1(url)
        if hasil.get("status"):
            return hasil["decoded_url"]
        return ""
    except:
        return ""


# ==========================
# AMBIL ISI BERITA
# ==========================

def ambil_isi(url):
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20
        )

        soup = BeautifulSoup(r.text, "html.parser")

        teks = []

        for p in soup.find_all("p"):
            isi = p.get_text(" ", strip=True)
            if len(isi) > 40:
                teks.append(isi)

        return " ".join(teks)

    except:
        return ""


# ==========================
# KATEGORI
# ==========================

def kategori_sektor(judul):

    t = judul.lower()

    skor = {
        "Pertanian/Primer": 0,
        "Manufaktur/Sekunder": 0,
        "Jasa/Tersier": 0
    }

    # =========================
    # PRIMER (PERTANIAN)
    # =========================
    bobot_primer = {
        "panen": 3,
        "petani": 3,
        "pertanian": 3,
        "jagung": 2,
        "kelapa": 2,
        "kopra": 2,
        "nelayan": 3,
        "ikan": 2,
        "laut": 2,
        "tambang": 3
    }

    for kata, bobot in bobot_primer.items():
        if kata in t:
            skor["Pertanian/Primer"] += bobot

    # =========================
    # SEKUNDER (INDUSTRI)
    # =========================
    bobot_sekunder = {
        "industri": 3,
        "pabrik": 3,
        "produksi": 2,
        "pengolahan": 2,
        "manufaktur": 3,
        "konstruksi": 3,
        "pembangunan": 2,
        "proyek": 2,
        "bangunan": 2
    }

    for kata, bobot in bobot_sekunder.items():
        if kata in t:
            skor["Manufaktur/Sekunder"] += bobot

    # =========================
    # TERSIER (JASA)
    # =========================
    bobot_tersier = {
        "perdagangan": 2,
        "pasar": 2,
        "umkm": 2,
        "usaha": 1,
        "jasa": 2,
        "pariwisata": 3,
        "hotel": 3,
        "transportasi": 2,
        "pendidikan": 3,
        "kesehatan": 3,
        "pemerintah": 2,
        "gedung": 2,
        "kantor": 2,
        "perpustakaan": 3,
        "sekolah": 3,
        "rs": 3,
        "rumah sakit": 3,
        "puskesmas": 3
    }

    for kata, bobot in bobot_tersier.items():
        if kata in t:
            skor["Jasa/Tersier"] += bobot

    # =========================
    # AMBIL HASIL TERTINGGI
    # =========================
    kategori_terbaik = max(skor, key=skor.get)
    nilai_terbaik = skor[kategori_terbaik]

    # =========================
    # FILTER KEPASTIAN
    # =========================
    if nilai_terbaik == 0:
        return "Tidak Teridentifikasi"

    return kategori_terbaik

# ==========================
# MODEL AI
# ==========================

@st.cache_resource
def load_model():

    model_name = "csebuetnlp/mT5_multilingual_XLSum"

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    return tokenizer, model


def ringkas_ai(teks, tokenizer, model):

    try:
        teks = teks[:1500]

        inputs = tokenizer(
            teks,
            return_tensors="pt",
            truncation=True,
            max_length=256
        )

        output = model.generate(
            **inputs,
            max_new_tokens=80,
            min_new_tokens=30,
            num_beams=2
        )

        return tokenizer.decode(
            output[0],
            skip_special_tokens=True
        )

    except:
        return ""


# ==========================
# SESSION
# ==========================

if "df" not in st.session_state:
    st.session_state.df = None


# ==========================
# AMBIL BERITA
# ==========================

if st.button("🚀 Ambil Berita"):

    with st.spinner("Mengambil berita..."):
        df = ambil_berita(
            queries,
            start_month,
            end_month,
            tahun,
            jumlah
        )

    if len(df) == 0:
        st.warning("Tidak ada berita ditemukan")

    else:

        with st.spinner("Mengambil isi berita..."):
            df["link_asli"] = df["link"].apply(decode_google_news)
            df["isi_berita"] = df["link_asli"].apply(ambil_isi)

        df["kategori_sektor"] = df["judul"].apply(kategori_sektor)

        st.session_state.df = df


# ==========================
# OUTPUT
# ==========================

if st.session_state.df is not None:

    df = st.session_state.df


    # ======================
    # DASHBOARD
    # ======================

    st.subheader("📊 Dashboard Sektor")

    sektor_count = df["kategori_sektor"].value_counts().reset_index()
    sektor_count.columns = ["Sektor", "Jumlah"]

    fig = px.bar(
        sektor_count,
        x="Sektor",
        y="Jumlah",
        text="Jumlah",
        title="Distribusi Sektor Berita"
    )

    st.plotly_chart(fig, use_container_width=True)


    # ======================
    # TABEL
    # ======================

    st.subheader("📋 Data Berita")

    st.dataframe(
        df[
            [
                "judul",
                "tanggal_terbit",
                "sumber",
                "kategori_sektor",
                "isi_berita"
            ]
        ],
        height=500,
        use_container_width=True
    )


    # ======================
    # FILTER RINGKASAN
    # ======================

    df_ringkas = df[df["kategori_sektor"].isin(kategori_pilih)]


    ringkas = st.checkbox("🤖 Buat Ringkasan AI")

    if ringkas:

        with st.spinner("AI sedang meringkas..."):

            tokenizer, model = load_model()

            df_ringkas["ringkasan"] = df_ringkas["isi_berita"].apply(
                lambda x: ringkas_ai(x, tokenizer, model)
            )

        st.subheader("🧠 Ringkasan AI (Filtered)")

        st.dataframe(
            df_ringkas[
                ["judul", "kategori_sektor", "ringkasan"]
            ],
            use_container_width=True
        )


        # ======================
        # DOWNLOAD EXCEL RINGKASAN
        # ======================

        output_ringkasan = BytesIO()

        with pd.ExcelWriter(
            output_ringkasan,
            engine="openpyxl"
        ) as writer:

            df_ringkas[
                [
                    "tanggal_terbit",
                    "judul",
                    "sumber",
                    "kategori_sektor",
                    "ringkasan",
                    "link_asli"
                ]
            ].to_excel(
                writer,
                index=False,
                sheet_name="Ringkasan_AI"
            )


        st.download_button(
            "📥 Download Excel Ringkasan AI",
            data=output_ringkasan.getvalue(),
            file_name="ringkasan_ai_tidore.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    # ======================
    # DOWNLOAD EXCEL
    # ======================

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Berita")

    st.download_button(
        "📥 Download Excel",
        data=output.getvalue(),
        file_name="berita_tidore.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )