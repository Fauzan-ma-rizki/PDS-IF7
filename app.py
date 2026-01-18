import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, HeatMap
import os

# ===================== KONFIGURASI =====================
st.set_page_config(
    page_title="Sistem Pemetaan Analisis (SIPETA) UMKM Kuliner",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== KOORDINAT =====================
KOTA_COORDS = {
    "Kota Bandung": (-6.9175, 107.6191),
    "Kab. Bandung": (-7.0251, 107.5197),
    "Kab. Bandung Barat": (-6.8452, 107.4478),
    "Kota Bogor": (-6.5971, 106.8060),
    "Kab. Bogor": (-6.4797, 106.8249),
    "Kota Depok": (-6.4025, 106.7942),
    "Kota Bekasi": (-6.2383, 106.9756),
    "Kab. Bekasi": (-6.2651, 107.1265),
    "Kab. Karawang": (-6.3073, 107.2931),
    "Kab. Garut": (-7.2232, 107.9000),
}

# ===================== HELPER =====================
def group_kategori(kat):
    kat = str(kat).lower()
    if any(x in kat for x in ['bakso', 'mie', 'bakmie']):
        return '🍜 Mie & Bakso'
    if any(x in kat for x in ['ayam', 'lele', 'sate', 'bebek']):
        return '🍗 Lauk Bakar/Goreng'
    if any(x in kat for x in ['padang', 'soto', 'nasi']):
        return '🍚 Nasi & Soto'
    if any(x in kat for x in ['dimsum', 'snack', 'roti', 'kue']):
        return '🥟 Camilan'
    return '🍽️ Kuliner Lainnya'

# ===================== LOAD DATA =====================
@st.cache_data
def load_data():
    if not os.path.exists("data_jabar_umkm.csv"):
        return None
    df = pd.read_csv("data_jabar_umkm.csv")
    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0)
    df['Kelompok_Bisnis'] = df['Kategori'].apply(group_kategori)
    return df

df = load_data()
if df is None:
    st.error("❌ File data_jabar_umkm.csv tidak ditemukan")
    st.stop()

# ===================== SIDEBAR =====================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3222/3222640.png", width=80)
    st.title("Dashboard UMKM")

    menu = st.radio(
        "Navigasi",
        [
            "💎 Ringkasan Data",
            "📈 Visualisasi Data",
            "🗺️ Pemetaan UMKM",
            "📋 Data Mentah"
        ]
    )

    st.subheader("📍 Filter Wilayah Global")
    wilayah_sidebar = st.selectbox(
        "Pilih Wilayah",
        ["Seluruh Jawa Barat"] + list(KOTA_COORDS.keys())
    )

# ===================== FILTER =====================
f_df = df.copy()
if wilayah_sidebar != "Seluruh Jawa Barat":
    f_df = f_df[f_df['Wilayah'] == wilayah_sidebar]

# ===================== MENU 1 =====================
if menu == "💎 Ringkasan Data":
    st.title(f"📊 Ringkasan Analisis UMKM – {wilayah_sidebar}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total UMKM", len(f_df))
    c2.metric("Rata-rata Rating", f"{f_df['Rating'].mean():.2f}")
    c3.metric("Sektor Terpadat", f_df['Kelompok_Bisnis'].mode()[0])
    c4.metric("Potensi Pasar", "Tinggi" if f_df['Rating'].mean() < 4.3 else "Menengah")

    fig = px.sunburst(
        f_df,
        path=['Kelompok_Bisnis', 'Kategori'],
        values='Rating',
        title="Struktur Pasar Kuliner"
    )
    st.plotly_chart(fig, use_container_width=True)

# ===================== MENU 2 =====================
elif menu == "📈 Visualisasi Data":
    st.title("📈 Analisis Kompetisi UMKM")

    comp = f_df.groupby('Kategori').agg(
        Total=('Nama', 'count'),
        Avg_Rating=('Rating', 'mean')
    ).reset_index()

    fig = px.bar(
        comp.sort_values('Total', ascending=False),
        x='Kategori',
        y='Total',
        color='Avg_Rating',
        title="Jumlah UMKM per Kategori"
    )
    st.plotly_chart(fig, use_container_width=True)

# ===================== MENU 3 (PEMETAAN) =====================
elif menu == "🗺️ Pemetaan UMKM":
    st.title("🗺️ Pemetaan & Pencarian UMKM")

    col_map, col_filter = st.columns([3, 1])

    with col_filter:
        st.subheader("🔍 Pencarian Peta")
        keyword = st.text_input("Cari Nama UMKM")
        show_heatmap = st.checkbox("Aktifkan Heatmap")

    # Ambil data dasar berdasarkan filter wilayah 
    map_df = f_df.dropna(subset=['lat', 'lng']).copy()

    # Filter data berdasarkan keyword pencarian 
    if keyword.strip():
        map_df = map_df[map_df['Nama'].str.contains(keyword, case=False, na=False)]

    selected_umkm = None
    if not map_df.empty:
        # Dropdown otomatis berisi UMKM dari wilayah yang dipilih 
        options = ["-- Lihat Semua --"] + sorted(map_df['Nama'].unique().tolist())
        choice = st.selectbox("📌 Fokus ke UMKM spesifik", options)
        if choice != "-- Lihat Semua --":
            selected_umkm = choice

    with col_map:
        if map_df.empty:
            st.warning(f"❌ Tidak ada data UMKM ditemukan")
        else:
            # Tentukan titik tengah dasar 
            center = KOTA_COORDS.get(wilayah_sidebar, (-6.9175, 107.6191))
            m = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron", control_scale=True)

            # LOGIKA ZOOM: Pilih salah satu (Zoom Spesifik ATAU Lihat Semua)
            if selected_umkm:
                # Ambil data UMKM yang dipilih
                r = map_df[map_df['Nama'] == selected_umkm].iloc[0]
                m = folium.Map(
                   location = [r['lat'], r['lng']],
                   zoom_start = 18,
                   title="CartoDB positron" 
                )
                
                # Tambahkan Marker Bintang Merah
                folium.Marker(
                    [r['lat'], r['lng']], 
                    popup=f"<b>{r['Nama']}</b>", 
                    icon=folium.Icon(color='red', icon='star')
                ).add_to(m)
            
                js = f"""
                <script>
                 setTimeout(function(){{
                 map.setView([{r['lat']}, {r['lng']}], 18);                                      
                }}, 300);
                 </script>                                        
                """ 
                m.get_root().html.add_child(folium.Element(js))
                
            else:
                sw = map_df[['lat', 'lng']].min().values.tolist()
                ne = map_df[['lat', 'lng']].max().values.tolist()
                m.fit_bounds([sw, ne])

            # Tambahkan Heatmap & Cluster 
            if show_heatmap:
                HeatMap(map_df[['lat', 'lng']].values.tolist()).add_to(m)

            cluster = MarkerCluster().add_to(m)
            for _, row in map_df.iterrows():
                if selected_umkm and row['Nama'] == selected_umkm:
                    continue
                folium.Marker(
                    [row['lat'], row['lng']],
                    popup=f"<b>{row['Nama']}</b><br>⭐ {row['Rating']}",
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(cluster)

            # Gunakan gabungan nama wilayah dan nama UMKM sebagai ID unik
            map_id = f"map_{wilayah_sidebar}_{selected_umkm}".replace(" ", "_")
            st_folium(m, width="100%", height=550, key=map_id, returned_objects=[])
            
    # ===== BAGIAN TABEL DATA ======
    st.markdown("---")
    st.subheader(f"📋 Daftar UMKM: {wilayah_sidebar}")
    if not map_df.empty:
        display_table = map_df[['Nama', 'Wilayah', 'Kategori', 'Rating']].copy()
        display_table.index = range(1, len(display_table) + 1)
        st.dataframe(display_table, use_container_width=True)
    else:
        st.info("Pilih wilayah di sidebar untuk melihat daftar UMKM.")
# ===================== MENU 4 =====================
elif menu == "📋 Data Mentah":
    st.title("📋 Data Mentah UMKM")
    st.dataframe(df, use_container_width=True)

# ===================== FOOTER =====================
st.sidebar.markdown("---")
st.sidebar.caption("© SIPETA 2026")