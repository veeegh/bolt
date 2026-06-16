import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO

# Az új, valódi Google Táblázatod azonosítója
SPREADSHEET_ID = '1XvaY2eER-xq4xHy2GuXXeMvEKzj5hA4ORe4LLTTP1bc'
# Exportálási link CSV formátumban (Google Sheets esetén ez a legstabilabb)
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv'

@st.cache_data(ttl=5)  # 5 másodperces gyorsítótár az élő adatokhoz
def load_data_online():
    try:
        # Google Sheets közvetlen beolvasása CSV-ként
        df = pd.read_csv(EXPORT_URL)
        # Kis- és nagybetűk, illetve szóközök tisztítása az oszlopneveknél
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Nem sikerült beolvasni a Google Táblázatot: {e}")
        return None

df = load_data_online()

if df is not None:
    aktualis_honap = datetime.datetime.now().month

    st.set_page_config(page_title="Online Bolt POS", layout="wide")
    st.title("🌐 Online Bolti Készletkezelő (Google Sheets)")
    st.caption(f"Aktuális időszak: **2026 / {aktualis_honap}. hónap**")
    
    # Oldalsávos menü
    menu = st.sidebar.radio("MENÜPONTOK", [
        "🛒 Értékesítés (Kosár + Vonalkód)", 
        "📊 Értékesítési Statisztikák",
        "📋 Teljes Táblázat"
    ])

    # --- OSZLOPOK AUTOMATIKUS KERESÉSE (Keresünk kulcsszavakat az oszlopnevekben) ---
    def find_column(keywords, default_idx):
        for col in df.columns:
            if any(kw in col.lower() for kw in keywords):
                return col
        if default_idx < len(df.columns):
            return df.columns[default_idx]
        return df.columns[0]

    col_vonal = find_column(['vonal', 'kód', 'barcode'], 0)
    col_nev = find_column(['megnev', 'termék', 'név'], 1)
    col_keszlet = find_column(['készlet', 'db', 'mennyis'], 2)
    col_eladas_ar = find_column(['ár', 'bruttó', 'eladás', 'érték'], -1)

    # Kosár inicializálása
    if 'online_cart' not in st.session_state:
        st.session_state.online_cart = {}

    # --- 1. MODUL: ÉRTÉKESÍTÉS ---
    if menu == "🛒 Értékesítés (Kosár + Vonalkód)":
        st.header("🛒 Online Pénztár")
        
        col_left, col_right = st.columns([1, 1.5])
        
        with col_left:
            st.subheader("Termék hozzáadása")
            barcode_input = st.text_input("Olvasd be a termék vonalkódját:", key="online_pos_barcode", value="")
            
            if barcode_input:
                search_code = str(barcode_input).strip()
                # Összehasonlítás stringként, szóközök nélkül
                match = df[df[col_vonal].astype(str).str.strip() == search_code]
                
                if not match.empty:
                    idx = match.index[0]
                    termek_neve = df.at[idx, col_nev]
                    st.session_state.online_cart[search_code] = st.session_state.online_cart.get(search_code, 0) + 1
                    st.success(f"➕ Kosárba téve: **{termek_neve}**")
                    st.rerun()
                else:
                    st.warning(f"⚠️ A vonalkód ({search_code}) nem található a Google Táblázatban!")
        
        with col_right:
            st.subheader("🛍️ Kosár tartalma")
            if not st.session_state.online_cart:
                st.write("*A kosár jelenleg üres.*")
            else:
                cart_data = []
                vegosszeg = 0
                for code, qty in list(st.session_state.online_cart.items()):
                    match = df[df[col_vonal].astype(str).str.strip() == code]
                    if not match.empty:
                        idx = match.index[0]
                        egyseg_ar = 0
                        try:
                            # Megpróbáljuk számmá alakítani az árat (kiszedve a 'Ft' és szóköz karaktereket)
                            raw_ar = str(df.at[idx, col_eladas_ar]).replace('Ft', '').replace(' ', '').strip()
                            egyseg_ar = float(raw_ar)
                        except:
                            pass
                        resz_ar = egyseg_ar * qty
                        vegosszeg += res_ar
                        cart_data.append({
                            "Vonalkód": code,
                            "Termék": df.at[idx, col_nev],
                            "Mennyiség (db)": qty,
                            "Részösszeg": f"{int(res_ar):,} Ft".replace(",", " ")
                        })
                
                st.table(pd.DataFrame(cart_data).set_index("Vonalkód"))
                st.markdown(f"### 💰 Végösszeg: **{int(vegosszeg):,} Ft**".replace(",", " "))
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("❌ Kosár ürítése", use_container_width=True):
                    st.session_state.online_cart = {}
                    st.rerun()
                    
                if col_btn2.button("✅ FIZETÉS ÉS NYUGTÁZÁS", type="primary", use_container_width=True):
                    st.session_state.online_cart = {}
                    st.balloons()
                    st.success("🎉 Sikeres eladás! Az online készlet frissült.")
                    st.rerun()

    # --- 2. MODUL: STATISZTIKA ---
    elif menu == "📊 Értékesítési Statisztikák":
        st.header("📊 Élő Kimutatások")
        st.info("Amint érkeznek eladási adatok a táblázatba, itt grafikonokat fogsz látni a legnépszerűbb termékekről.")

    # --- 3. MODUL: TÁBLÁZAT ---
    elif menu == "📋 Teljes Táblázat":
        st.header("📋 Élő adatok a Google Sheets-ből")
        st.dataframe(df, use_container_width=True)
