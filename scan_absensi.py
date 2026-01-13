import streamlit as st
import pandas as pd
from datetime import datetime, time
from pyzbar.pyzbar import decode
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =============================
# KONFIGURASI
# =============================
JAM_MULAI = time(7, 0)
JAM_SELESAI = time(16, 0)

SHEET_ABSENSI = "absensi"
SHEET_BULANAN = "rekap_bulanan"

# =============================
# STREAMLIT CONFIG
# =============================
st.set_page_config(
    page_title="Absensi QR Kampus",
    page_icon="📷",
    layout="centered"
)

st.title("📷 Absensi QR Code Kampus")
st.write("Silakan scan QR Code untuk melakukan absensi")

# =============================
# GOOGLE SHEETS CONNECT
# =============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)

client = gspread.authorize(creds)

SPREADSHEET = client.open_by_key(
    st.secrets["SPREADSHEET_ID"]
)

sheet_absen = SPREADSHEET.worksheet(SHEET_ABSENSI)
sheet_bulan = SPREADSHEET.worksheet(SHEET_BULANAN)

# =============================
# TANGGAL & JAM
# =============================
tanggal = datetime.now().strftime("%Y-%m-%d")
bulan = datetime.now().strftime("%Y-%m")
jam_sekarang = datetime.now().time()

st.info(f"""
📅 **Tanggal:** {tanggal}  
⏰ **Jam Absensi:** 07.00 – 16.00
""")

# =============================
# CEK JAM
# =============================
if not (JAM_MULAI <= jam_sekarang <= JAM_SELESAI):
    st.error("⛔ Absensi hanya dapat dilakukan pukul 07.00 – 16.00")
    st.stop()

# =============================
# LOAD DATA ABSENSI
# =============================
data_absen = sheet_absen.get_all_records()
df_absen = pd.DataFrame(data_absen)

if not df_absen.empty:
    df_absen["NPM"] = df_absen["NPM"].astype(str)

# =============================
# SCAN QR
# =============================
st.subheader("📸 Scan QR Code")
img_file = st.camera_input("Arahkan kamera ke QR Code")

if img_file:
    image = Image.open(img_file)
    qr = decode(image)

    if not qr:
        st.warning("⚠️ QR Code tidak terdeteksi")
    else:
        try:
            npm, nama, prodi = qr[0].data.decode().split("|")
            npm = str(npm)
        except:
            st.error("❌ Format QR Code tidak valid")
            st.stop()

        # =============================
        # CEK ABSENSI HARI INI
        # =============================
        sudah_absen = (
            (df_absen["NPM"] == npm) &
            (df_absen["Tanggal"] == tanggal)
        ).any()

        if sudah_absen:
            st.warning(f"⚠️ **{nama} sudah melakukan absensi hari ini**")
        else:
            sheet_absen.append_row([
                npm,
                nama,
                prodi,
                tanggal,
                datetime.now().strftime("%H:%M:%S")
            ])

            st.success(f"✅ **Absensi berhasil**\n\n{npm} - {nama}")

# =============================
# REKAP BULANAN OTOMATIS
# =============================
def update_rekap_bulanan():
    if df_absen.empty:
        return

    df_bulan = df_absen[df_absen["Tanggal"].str.startswith(bulan)]

    rekap = (
        df_bulan.groupby(["NPM", "Nama"])
        .size()
        .reset_index(name="Jumlah Hadir")
    )

    sheet_bulan.clear()
    sheet_bulan.append_row(["NPM", "Nama", "Bulan", "Jumlah Hadir"])

    for _, row in rekap.iterrows():
        sheet_bulan.append_row([
            row["NPM"],
            row["Nama"],
            bulan,
            int(row["Jumlah Hadir"])
        ])

update_rekap_bulanan()

# =============================
# ADMIN VIEW
# =============================
with st.expander("📊 Kehadiran Hari Ini"):
    if df_absen.empty:
        st.info("Belum ada absensi")
    else:
        st.dataframe(df_absen[df_absen["Tanggal"] == tanggal])

with st.expander("📅 Rekap Bulanan"):
    data_bulan = sheet_bulan.get_all_records()
    if data_bulan:
        st.dataframe(pd.DataFrame(data_bulan))
    else:
        st.info("Belum ada rekap bulanan")
