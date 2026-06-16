import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO

# 1. Google Táblázat azonosító
SPREADSHEET_ID = '10QStBpYSinhy9y6pCn6Kk9tUfzbIGPKwESJZR_33gj0'
# 2. A fül pontos neve
SHEET_NAME = '2026. JÚNIUS'

# Visszaváltunk az Excel (.xlsx) alapú letöltésre, mert az tökéletesen kezeli a te kétrétegű fejlécedet!
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx'

@st.cache_data(ttl=2)
def load_data_online():
    try:
        response = requests.get(EXPORT_URL)
        # Beolvasás úgy, hogy az első két sort fejlécként kezeljük
        df = pd.read_excel(BytesIO(response.content), header=[0, 1])
        # Tisztítjuk a neveket
        df.columns = pd.MultiIndex.from_tuples([(str(a).strip(), str(b).strip()) for a, b in df.columns])
        return df
    except Exception as e:
        st.error(f"Hiba a beolvasáskor: {e}")
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

    # --- OKOS OSZLOP-BEAZONOSÍTÁS ---
    # Megkeressük a vonalkódot, megnevezést és árat a te táblázatod képe alapján
    try:
        col_vonal = [c for c in df.columns if 'vonalkód' in str(c[0]).lower() or 'vonalkód' in str(c[1]).lower()][0]
    except:
        col_vonal = df.columns[7] # H oszlop

    try:
        col_nev = [c for c in df.columns if 'megnevezés' in str(c[0]).lower() or 'megnevezés' in str(c[1]).lower()][0]
    except:
        col_nev = df.columns[1] # B oszlop

    try:
        col_eladas_ar = [c for c in df.columns if 'bruttó' in str(c[0]).lower() and 'eladás' in str(c[1]).lower()][0]
    except:
        col_eladas_ar = df.columns[4] # E oszlop

    # Kosár inicializálása
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
                
                # Vonalkód oszlop letisztítása a kereséshez
                df_clean = df.copy()
                df_clean['clean_barcode'] = df_clean[col_vonal].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

                match = df_clean[df_clean['clean_barcode'] == search_code]

                if not match.empty:
                    idx = match.index[0]
                    termek_neve = df.at[idx, col_nev]
                    
                    # Ár kiszedése
                    egyseg_ar = 0
                    try:
                        raw_ar = str(df.at[idx, col_eladas_ar]).replace('Ft', '').replace(' ', '').replace('\xa0', '').strip()
                        egyseg_ar = int(float(raw_ar))
                    except:
                        pass

                    # Kosárba rakás
                    st.session_state.online_cart_list.append({
                        "vonalkod": search_code,
                        "nev": termek_neve,
                        "ar": egyseg_ar
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
                raw_cart_df = pd.DataFrame(st.session_state.online_cart_list)
                summary_df = raw_cart_df.groupby(['vonalkod', 'nev']).agg(
                    Mennyiség=('ar', 'count'),
                    Egységár=('ar', 'first')
                ).reset_index()
                
                summary_df['Részösszeg_Int'] = summary_df['Mennyiség'] * summary_df['Egységár']
                
                display_df = pd.DataFrame()
                display_df['Vonalkód'] = summary_df['vonalkod']
                display_df['Termék'] = summary_df['nev']
                display_df['Mennyiség (db)'] = summary_df['Mennyiség']
                display_df['Részösszeg'] = summary_df['Részösszeg_Int'].apply(lambda x: f"{int(x):,} Ft".replace(",", " "))
                
                vegosszeg = summary_df['Részösszeg_Int'].sum()
                
                st.table(display_df.set_index("Vonalkód"))
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
        # Sima, tiszta megjelenítés
        st.dataframe(df, use_container_width=True)
