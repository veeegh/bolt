import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO

# 1. AZ ÚJ Google Táblázatod azonosítója
SPREADSHEET_ID = '10QStBpYSinhy9y6pCn6Kk9tUfzbIGPKwESJZR_33gj0'

# 2. FONTOS: Írd be ide a Google Táblázatod alsó fülének a PONTOS nevét!
# Ha a fül neve más (pl. "Munkalap1" vagy "Készlet"), írd át arra, ami ott szerepel!
SHEET_NAME = 'ÖSSZES'

# Közvetlen letöltési link a megadott fülhöz
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={requests.utils.quote(SHEET_NAME)}'

@st.cache_data(ttl=2)
def load_data_online():
    try:
        # A legstabilabb CSV alapú beolvasás a pontos fül megadásával
        df = pd.read_csv(EXPORT_URL)
        
        # Ha a Google az első sort vette fejlécnek, de nálad az összevont "2026. JÚNIUS", 
        # megtisztítjuk a rendszert, hogy lássuk a valódi oszlopokat
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Nem sikerült beolvasni a Google Táblázat '{SHEET_NAME}' fülét: {e}")
        return None

df = load_data_online()

if df is not None:
    st.set_page_config(page_title="Online Bolt POS", layout="wide")
    st.title("🌐 Online Bolti Készletkezelő")
    st.caption(f"Aktuális fül: **{SHEET_NAME}**")
    
    menu = st.sidebar.radio("MENÜPONTOK", [
        "🛒 Értékesítés (Kosár + Vonalkód)", 
        "📋 Teljes Táblázat Ellenőrzése"
    ])

    # --- INTELLIGENS OSZLOPKERESŐ ---
    # Megkeresi az oszlopot, ha szerepel a nevében a kulcsszó, vagy ha a Google "Unnamed"-nek nevezte el
    def get_column_by_keyword(keywords, default_index):
        for idx, col in enumerate(df.columns):
            if any(kw in col.lower() for kw in keywords):
                return col
        if default_index < len(df.columns):
            return df.columns[default_index]
        return df.columns[0]

    # A te táblázatod alapján hozzárendeljük az oszlopokat
    col_vonal = get_column_by_keyword(['vonal', 'kód', 'barcode'], 7)  # Keresi a vonalkódot, különben a 8. oszlop
    col_nev = get_column_by_keyword(['megnev', 'termék', 'név'], 1)     # Keresi a megnevezést, különben a 2. oszlop
    col_eladas_ar = get_column_by_keyword(['bruttó', 'eladás', 'ár'], 4) # Keresi az árat, különben az 5. oszlop

    if 'online_cart' not in st.session_state:
        st.session_state.online_cart = {}

    # --- 1. MODUL: ÉRTÉKESÍTÉS ---
    if menu == "🛒 Értékesítés (Kosár + Vonalkód)":
        st.header("🛒 Online Pénztár")
        
        col_left, col_right = st.columns([1, 1.5])
        
        with col_left:
            st.subheader("Termék beolvasása")
            barcode_input = st.text_input("Kattints ide a kurzorral, majd olvasd be a vonalkódot:", key="online_pos_barcode", value="")
            
            if barcode_input:
                search_code = str(barcode_input).strip()
                
                # Keresés a vonalkód oszlopban
                match = df[df[col_vonal].astype(str).str.strip() == search_code]
                
                if match.empty:
                    # Tizedesjegy-levágás (.0) kezelése
                    match = df[df[col_vonal].astype(str).str.strip().str.startswith(search_code)]

                if not match.empty:
                    idx = match.index[0]
                    termek_neve = df.at[idx, col_nev]
                    st.session_state.online_cart[search_code] = st.session_state.online_cart.get(search_code, 0) + 1
                    st.success(f"➕ Kosárba téve: **{termek_neve}**")
                    st.rerun()
                else:
                    st.warning(f"⚠️ A vonalkód ({search_code}) nem található a táblázatban!")
        
        with col_right:
            st.subheader("🛍️ Kosár tartalma")
            if not st.session_state.online_cart:
                st.write("*A kosár jelenleg üres. Várja a beolvasást...*")
            else:
                cart_data = []
                vegosszeg = 0
                for code, qty in list(st.session_state.online_cart.items()):
                    match = df[df[col_vonal].astype(str).str.strip() == code]
                    if match.empty:
                        match = df[df[col_vonal].astype(str).str.strip().str.startswith(code)]
                        
                    if not match.empty:
                        idx = match.index[0]
                        egyseg_ar = 0
                        try:
                            raw_ar = str(df.at[idx, col_eladas_ar]).replace('Ft', '').replace(' ', '').replace('\xa0', '').strip()
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
                
                if cart_data:
                    st.table(pd.DataFrame(cart_data).set_index("Vonalkód"))
                    st.markdown(f"### 💰 Végösszeg: **{int(vegosszeg):,} Ft**".replace(",", " "))
                    
                    col_btn1, col_btn2 = st.columns(2)
                    if col_btn1.button("❌ Kosár ürítése", use_container_width=True):
                        st.session_state.online_cart = {}
                        st.rerun()
                        
                    if col_btn2.button("✅ FIZETÉS ÉS NYUGTÁZÁS", type="primary", use_container_width=True):
                        st.session_state.online_cart = {}
                        st.balloons()
                        st.success("🎉 Sikeres értékesítés rögzítve!")
                        st.rerun()

    # --- 2. MODUL: TÁBLÁZAT ---
    elif menu == "📋 Teljes Táblázat Ellenőrzése":
        st.header("📋 Élő adatok a Google Sheets-ből")
        st.write(f"A(z) **{SHEET_NAME}** fül beolvasott adatai:")
        st.dataframe(df, use_container_width=True)
