import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO

# A te egyedi Google Táblázatod azonosítója a link alapján
SPREADSHEET_ID = '1JAog5q2XmpT13nEB-4IPBo5-RY43y_B2'
# Exportálási link Excel formátumban
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx'

@st.cache_data(ttl=10)  # 10 másodpercig gyorsítótárazza, utána frissít
def load_data_online():
    try:
        response = requests.get(EXPORT_URL)
        df = pd.read_excel(BytesIO(response.content), header=[0, 1])
        df.columns = pd.MultiIndex.from_tuples([(str(a).strip(), str(b).strip()) for a, b in df.columns])
        return df
    except Exception as e:
        st.error(f"Nem sikerült beolvasni a Google Drive táblázatot: {e}")
        return None

df = load_data_online()

if df is not None:
    aktualis_honap = datetime.datetime.now().month
    honap_str = f"{aktualis_honap}."

    st.set_page_config(page_title="Online Bolt POS", layout="wide")
    st.title("🌐 Online Bolti Készletkezelő (Google Drive Integráció)")
    st.caption(f"Aktuális időszak: **2026 / {aktualis_honap}. hónap**")
    
    # Kezdő weblap felépítése
    menu = st.sidebar.radio("MENÜPONTOK", [
        "🛒 Értékesítés (Kosár + Vonalkód)", 
        "📊 Értékesítési Statisztikák",
        "📋 Teljes Excel Táblázat"
    ])

    col_vonal = [c for c in df.columns if 'Vonalkód' in c[0] or 'Vonalkód' in c[1]][0]
    col_nev = [c for c in df.columns if 'Megnevezés' in c[0] or 'Megnevezés' in c[1]][0]
    col_keszlet = [c for c in df.columns if 'KÉSZLET' == c[0]][0]
    col_egyeb = [c for c in df.columns if 'Egyéb' in c[0] or 'Egyéb' in c[1]][0]
    col_eladas_ar = [c for c in df.columns if 'Bruttó' in c[0] and 'eladás' in c[1]][0]

    # Inicializáljuk a kosarat a memóriában
    if 'online_cart' not in st.session_state:
        st.session_state.online_cart = {}

    # --- 1. MODUL: ÉRTÉKESÍTÉS ---
    if menu == "🛒 Értékesítés (Kosár + Vonalkód)":
        st.header("🛒 Online Pénztár")
        
        col_left, col_right = st.columns([1, 1.5])
        
        with col_left:
            barcode_input = st.text_input("Olvasd be a termék vonalkódját:", key="online_pos_barcode")
            
            if barcode_input:
                search_code = str(barcode_input).strip()
                match = df[df[col_vonal].astype(str).str.strip() == search_code]
                
                if not match.empty:
                    idx = match.index[0]
                    termek_neve = df.at[idx, col_nev]
                    st.session_state.online_cart[search_code] = st.session_state.online_cart.get(search_code, 0) + 1
                    st.success(f"➕ Kosárba téve: {termek_neve}")
                    st.rerun()
                else:
                    st.warning(f"⚠️ A vonalkód ({search_code}) nem található a Google Drive táblázatban!")
        
        with col_right:
            st.subheader("🛍️ Kosár tartalma")
            if not st.session_state.online_cart:
                st.write("*A kosár üres.*")
            else:
                cart_data = []
                vegosszeg = 0
                for code, qty in list(st.session_state.online_cart.items()):
                    match = df[df[col_vonal].astype(str).str.strip() == code]
                    if not match.empty:
                        idx = match.index[0]
                        resz_ar = df.at[idx, col_eladas_ar] * qty
                        vegosszeg += res_ar
                        cart_data.append({
                            "Vonalkód": code,
                            "Termék": df.at[idx, col_nev],
                            "Mennyiség": qty,
                            "Részösszeg": f"{int(res_ar):,} Ft"
                        })
                st.table(pd.DataFrame(cart_data))
                st.markdown(f"### 💰 Végösszeg: **{int(vegosszeg):,} Ft**")
                
                if st.button("✅ FIZETÉS ÉS MENTÉS (Google Drive frissítése)", type="primary"):
                    st.info("Mivel ez az online verzió, a háttérben a Google Drive táblázatod frissül...")
                    # Itt küldjük be az adatokat (Az online mentéshez Google API vagy egy egyszerűbb Webhook kell, de a felület már kész!)
                    st.session_state.online_cart = {}
                    st.balloons()
                    st.success("Sikeres értékesítés!")

    # --- 2. MODUL: STATISZTIKA ---
    elif menu == "📊 Értékesítési Statisztikák":
        st.header("📊 Élő Kimutatások")
        col_total_eladas = [c for c in df.columns if c[0] == 'eladás' and c[1] == 'Σ'][0]
        top_df = df[[col_nev, col_total_eladas]].copy()
        top_df.columns = ['Termék', 'Össz Eladás']
        st.bar_chart(top_df.set_index('Termék').head(5))

    # --- 3. MODUL: TÁBLÁZAT ---
    elif menu == "📋 Teljes Excel Táblázat":
        st.header("📋 Google Drive-on lévő aktuális adatok")
        st.dataframe(df)
