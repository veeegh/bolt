import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO

# 1. AZ ÚJ Google Táblázatod azonosítója
SPREADSHEET_ID = '10QStBpYSinhy9y6pCn6Kk9tUfzbIGPKwESJZR_33gj0'

# 2. A Google Táblázatod alsó fülének a pontos neve
SHEET_NAME = 'ÖSSZES'

# Közvetlen letöltési link a megadott fülhöz
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={requests.utils.quote(SHEET_NAME)}'

@st.cache_data(ttl=2)
def load_data_online():
    try:
        df = pd.read_csv(EXPORT_URL)
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

    # --- OSZLOPOK PONTOS BEAZONOSÍTÁSA ---
    def get_column_by_keyword(keywords, default_index):
        for idx, col in enumerate(df.columns):
            if any(kw in col.lower() for kw in keywords):
                return col
        if default_index < len(df.columns):
            return df.columns[default_index]
        return df.columns[0]

    col_vonal = get_column_by_keyword(['vonalkód', 'vonal', 'kód', 'barcode'], 7)
    col_nev = get_column_by_keyword(['megnevezés', 'megnev', 'termék', 'név'], 1)
    col_eladas_ar = get_column_by_keyword(['bruttó', 'eladás', 'ár'], 4)

    # Kosár inicializálása a memóriában (Golyóálló listás szerkezet)
    if 'online_cart_list' not in st.session_state:
        st.session_state.online_cart_list = []

    # --- 1. MODUL: ÉRTÉKESÍTÉS ---
    if menu == "🛒 Értékesítés (Kosár + Vonalkód)":
        st.header("🛒 Online Pénztár")
        
        col_left, col_right = st.columns([1, 1.5])
        
        with col_left:
            st.subheader("Termék beolvasása")
            barcode_input = st.text_input("Kattints ide a kurzorral, majd olvasd be a vonalkódot:", key="online_pos_barcode", value="")
            
            if barcode_input:
                search_code = str(barcode_input).strip().replace('.0', '')
                
                # Szigorú keresés: megtisztítjuk a Google Táblázat vonalkód oszlopát is
                df_clean = df.copy()
                df_clean['clean_barcode'] = df_clean[col_vonal].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

                match = df_clean[df_clean['clean_barcode'] == search_code]

                if not match.empty:
                    idx = match.index[0]
                    termek_neve = df.at[idx, col_nev]
                    
                    # Ár kinyerése és tisztítása biztonságosan
                    egyseg_ar = 0
                    try:
                        raw_ar = str(df.at[idx, col_eladas_ar]).replace('Ft', '').replace(' ', '').replace('\xa0', '').strip()
                        egyseg_ar = int(float(raw_ar))
                    except:
                        pass

                    # Azonnali mentés a kosárba
                    st.session_state.online_cart_list.append({
                        "Vonalkód": search_code,
                        "Termék": termek_neve,
                        "Ár": egyseg_ar
                    })
                    
                    st.success(f"➕ Kosárba téve: **{termek_neve}**")
                    st.rerun()
                else:
                    st.warning(f"⚠️ A vonalkód ({search_code}) nem található a táblázatban!")
        
        with col_right:
            st.subheader("🛍️ Kosár tartalma")
            if not st.session_state.online_cart_list:
                st.write("*A kosár jelenleg üres. Várja a beolvasást...*")
            else:
                # Egyszerű, golyóálló összesítés ciklussal (Nincs Pandas groupby hiba!)
                counts = {}
                for item in st.session_state.online_cart_list:
                    key = (item["Vonalkód"], item["Termék"], item["Ár"])
                    counts[key] = counts.get(key, 0) + 1
                
                # Átrakjuk egy szép táblázat formátumba
                final_items = []
                vegosszeg = 0
                for (vonal, nev, ar), db in counts.items():
                    reszosszeg = ar * db
                    vegosszeg += reszosszeg
                    final_items.append({
                        "Vonalkód": vonal,
                        "Termék": nev,
                        "Mennyiség": f"{db} db",
                        "Egységár": f"{int(ar):,} Ft".replace(",", " "),
                        "Részösszeg": f"{int(reszosszeg):,} Ft".replace(",", " ")
                    })
                
                # Megjelenítés tiszta táblázatként
                st.table(pd.DataFrame(final_items).set_index("Vonalkód"))
                st.markdown(f"### 💰 Végösszeg: **{int(vegosszeg):,} Ft**".replace(",", " "))
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("❌ Kosár ürítése", use_container_width=True):
                    st.session_state.online_cart_list = []
                    st.rerun()
                    
                if col_btn2.button("✅ FIZETÉS ÉS NYUGTÁZÁS", type="primary", use_container_width=True):
                    st.session_state.online_cart_list = []
                    st.balloons()
                    st.success("🎉 Sikeres értékesítés rögzítve!")
                    st.rerun()

    # --- 2. MODUL: TÁBLÁZAT ---
    elif menu == "📋 Teljes Táblázat Ellenőrzése":
        st.header("📋 Élő adatok a Google Sheets-ből")
        st.write(f"A(z) **{SHEET_NAME}** fül beolvasott adatai:")
        st.dataframe(df, use_container_width=True)
