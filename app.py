import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO

# AZ ÚJ Google Táblázatod pontos azonosítója
SPREADSHEET_ID = '10QStBpYSinhy9y6pCn6Kk9tUfzbIGPKwESJZR_33gj0'
# Exportálási link Excel formátumban (a kétrétegű fejléc megtartása miatt ez a legjobb)
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx'

@st.cache_data(ttl=2)  # 2 másodperces gyorsítótár a szinte azonnali élő frissítésekhez
def load_data_online():
    try:
        response = requests.get(EXPORT_URL)
        # Beolvassuk a táblázatot úgy, hogy az első 2 sort tekintjük a fejlécnek (Multi-index)
        df = pd.read_excel(BytesIO(response.content), header=[0, 1])
        # Megtisztítjuk az oszlopneveket a láthatatlan szóközöktől
        df.columns = pd.MultiIndex.from_tuples([(str(a).strip(), str(b).strip()) for a, b in df.columns])
        return df
    except Exception as e:
        st.error(f"Nem sikerült beolvasni a Google Táblázatot: {e}")
        return None

df = load_data_online()

if df is not None:
    st.set_page_config(page_title="Online Bolt POS", layout="wide")
    st.title("🌐 Online Bolti Készletkezelő")
    
    # Menüválasztó a bal oldali sávban
    menu = st.sidebar.radio("MENÜPONTOK", [
        "🛒 Értékesítés (Kosár + Vonalkód)", 
        "📋 Teljes Táblázat Ellenőrzése"
    ])

    # --- OSZLOPOK PONTOS BEAZONOSÍTÁSA A TE KÉPED ALAPJÁN ---
    try:
        col_vonal = [c for c in df.columns if 'vonalkód' in str(c[0]).lower() or 'vonalkód' in str(c[1]).lower()][0]
        col_nev = [c for c in df.columns if 'megnevezés' in str(c[0]).lower() or 'megnevezés' in str(c[1]).lower()][0]
        col_eladas_ar = [c for c in df.columns if 'bruttó' in str(c[0]).lower() and 'eladás' in str(c[1]).lower()][0]
    except Exception as e:
        # Biztonsági tartalék indexek alapján, ha a név szerinti keresés elcsúszna
        col_vonal = df.columns[7]      # H oszlop (Vonalkód)
        col_nev = df.columns[1]        # B oszlop (Megnevezés)
        col_eladas_ar = df.columns[4]  # E oszlop (Bruttó eladási ár)

    # Kosár inicializálása a memóriában
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
                
                # Keresés normál stringként
                match = df[df[col_vonal].astype(str).str.strip() == search_code]
                
                # Ha nem találja, megpróbálja levágni a tizedesjegyeket (.0), amiket a táblázat generálhat
                if match.empty:
                    match = df[df[col_vonal].astype(str).str.strip().str.startswith(search_code)]

                if not match.empty:
                    idx = match.index[0]
                    termek_neve = df.at[idx, col_nev]
                    st.session_state.online_cart[search_code] = st.session_state.online_cart.get(search_code, 0) + 1
                    st.success(f"➕ Kosárba téve: **{termek_neve}**")
                    st.rerun()
                else:
                    st.warning(f"⚠️ A vonalkód ({search_code}) nem található az új táblázatban!")
        
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
                            # Ár megtisztítása a formázástól (Ft, szóközök eltávolítása a matematikai számításhoz)
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
                        st.rerun
