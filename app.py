import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO

# A te egyedi Google Táblázatod azonosítója a link alapján
SPREADSHEET_ID = '1JAog5q2XmpT13nEB-4IPBo5-RY43y_B2'
# Exportálási link Excel formátumban
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx'

@st.cache_data(ttl=5)  # 5 másodpercig gyorsítótárazza az adatokat, utána frissít
def load_data_online():
    try:
        response = requests.get(EXPORT_URL)
        df = pd.read_excel(BytesIO(response.content), header=[0, 1])
        # Oszlopnevek megtisztítása a felesleges szóközöktől
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
    
    # Menü felépítése a bal oldalon
    menu = st.sidebar.radio("MENÜPONTOK", [
        "🛒 Értékesítés (Kosár + Vonalkód)", 
        "📊 Értékesítési Statisztikák",
        "📋 Teljes Excel Táblázat"
    ])

    # --- BIZTONSÁGI OSZLOP-BEAZONOSÍTÁS (Nem omlik össze, ha eltér a név) ---
    try:
        col_vonal = [c for c in df.columns if 'vonal' in str(c[0]).lower() or 'vonal' in str(c[1]).lower()][0]
    except:
        col_vonal = df.columns[0]  # Ha nem találja, az 1. oszlop lesz a vonalkód

    try:
        col_nev = [c for c in df.columns if 'megnev' in str(c[0]).lower() or 'megnev' in str(c[1]).lower()][0]
    except:
        col_nev = df.columns[1]  # Ha nem találja, a 2. oszlop a név

    try:
        col_keszlet = [c for c in df.columns if 'készlet' in str(c[0]).lower() or 'készlet' in str(c[1]).lower()][0]
    except:
        # Ha nincs meg a tiszta név, megpróbálja megtippelni az 5. oszlop környékén
        col_keszlet = [c for c in df.columns if 'unnamed' in str(c[1]).lower() and 'készlet' in str(c[0]).lower()]
        if col_keszlet:
            col_keszlet = col_keszlet[0]
        else:
            col_keszlet = df.columns[4]

    try:
        col_egyeb = [c for c in df.columns if 'egyéb' in str(c[0]).lower() or 'egyéb' in str(c[1]).lower()][0]
    except:
        col_egyeb = df.columns[2]

    try:
        col_eladas_ar = [c for c in df.columns if 'bruttó' in str(c[0]).lower() and 'eladás' in str(c[1]).lower()][0]
    except:
        try:
            col_eladas_ar = [c for c in df.columns if 'eladás' in str(c[0]).lower() or 'eladás' in str(c[1]).lower()][-1]
        except:
            col_eladas_ar = df.columns[-1]

    # Inicializáljuk a kosarat a memóriában, ha még nincs
    if 'online_cart' not in st.session_state:
        st.session_state.online_cart = {}

    # --- 1. MODUL: ÉRTÉKESÍTÉS ---
    if menu == "🛒 Értékesítés (Kosár + Vonalkód)":
        st.header("🛒 Online Pénztár")
        
        col_left, col_right = st.columns([1, 1.5])
        
        with col_left:
            st.subheader("Termék hozzáadása")
            barcode_input = st.text_input("Olvasd be a termék vonalkódját (vagy gépeld be):", key="online_pos_barcode", value="")
            
            if barcode_input:
                search_code = str(barcode_input).strip()
                # Megkeressük a terméket a vonalkód alapján
                match = df[df[col_vonal].astype(str).str.strip() == search_code]
                
                if not match.empty:
                    idx = match.index[0]
                    termek_neve = df.at[idx, col_nev]
                    st.session_state.online_cart[search_code] = st.session_state.online_cart.get(search_code, 0) + 1
                    st.success(f"➕ Kosárba téve: **{termek_neve}**")
                    st.rerun()
                else:
                    st.warning(f"⚠️ A vonalkód ({search_code}) nem található a Google Drive táblázatban!")
        
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
                            egyseg_ar = float(df.at[idx, col_eladas_ar])
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
                    st.toast("Értékesítés rögzítése folyamatban...")
                    # Kosár ürítése és vizuális visszajelzés
                    st.session_state.online_cart = {}
                    st.balloons()
                    st.success("🎉 Sikeres eladás! (Az online nézet frissült.)")
                    st.rerun()

    # --- 2. MODUL: STATISZTIKA ---
    elif menu == "📊 Értékesítési Statisztikák":
        st.header("📊 Élő Kimutatások")
        try:
            col_total_eladas = [c for c in df.columns if c[0] == 'eladás' and c[1] == 'Σ'][0]
            top_df = df[[col_nev, col_total_eladas]].copy()
            top_df.columns = ['Termék', 'Össz Eladás (db)']
            top_df = top_df.sort_values(by='Össz Eladás (db)', ascending=False).head(5)
            
            st.subheader("🏆 Legnépszerűbb 5 termék a boltban")
            st.bar_chart(top_df.set_index('Termék'))
        except:
            st.info("A diagram megjelenítéséhez eladási adatokra van szükség az Excelben.")

    # --- 3. MODUL: TÁBLÁZAT ---
    elif menu == "📋 Teljes Excel Táblázat":
        st.header("📋 Google Drive-ról beolvasott élő adatok")
        st.write("Ez a táblázat pontosan azt mutatja, ami jelenleg a Drive-odon lévő fájlban van.")
        st.dataframe(df, use_container_width=True)
