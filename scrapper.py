import time
import pandas as pd
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def scrape_jabar_raya(total_target=1500):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # DAFTAR 27 WILAYAH JAWA BARAT
    locations = {
    "Kota Bandung": (-6.9175, 107.6191), 
    "Kab. Bandung": (-7.0251, 107.5197), 
    "Kab. Bandung Barat": (-6.8452, 107.4478), 
    "Kota Bogor": (-6.5971, 106.8060),
    "Kab. Bogor": (-6.4797, 106.8249), 
    "Kota Depok": (-6.4025, 106.7942),
    "Kota Bekasi": (-6.2383, 106.9756), 
    "Kab. Bekasi": (-6.2651, 107.1265), 
    "Kab. Karawang": (-6.3073, 107.2931), 
    "Kab. Garut": (-7.2232, 107.9000)
    }
    
    categories = ["Bakso dan Mie Ayam", "Ayam Bakar", "Pecel Lele", "Sate","Nasi Padang", "Soto", "Nasi Goreng", "Bakmie", "Dimsum"]
    
    all_data = []
    
    # Setup Driver dengan penanganan error koneksi
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except:
        driver = webdriver.Chrome(options=chrome_options)

    print(f"=== Memulai Scraping Sistematis (Target Maksimal: {total_target} Data) ===")

    try:
        for loc_name, coords in locations.items():
            if len(all_data) >= total_target: break
            
            for cat in categories:
                if len(all_data) >= total_target: break
                
                query = f"{cat} di {loc_name}".replace(" ", "+")
                print(f"🔎 Mengambil data: {cat} di {loc_name}...")
                
                driver.get(f"http://www.google.com/maps/search/{query}")
                time.sleep(5) 

                try:
                    # Scroll lebih dalam agar mendapatkan lebih banyak data per kategori
                    scrollable_div = driver.find_element(By.XPATH, '//div[@role="feed"]')
                    for _ in range(5):
                        driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
                        time.sleep(1.5)
                except: pass

                # Ambil SEMUA data yang muncul
                places = driver.find_elements(By.CLASS_NAME, "hfpxzc")
                
                for p in places:
                    if len(all_data) >= total_target: break # Berhenti jika sudah 1500
                    try:
                        name = p.get_attribute("aria-label")
                        parent_text = p.find_element(By.XPATH, "./../../..").text
                        
                        # Rating
                        rating = 0.0
                        lines = parent_text.split('\n')
                        for line in lines:
                            if '(' in line and (',' in line or '.' in line):
                                try:
                                    rating = float(line.split('(')[0].strip().replace(',', '.'))
                                    break
                                except: continue

                        # Hindari duplikat nama
                        if name and name not in [d['Nama'] for d in all_data]:
                            all_data.append({
                                "Nama": name,
                                "Wilayah": loc_name,
                                "Kategori": cat,
                                "Rating": rating,
                                "Status": "Buka" if "Buka" in parent_text else "Tutup",
                                "lat": coords[0] + random.uniform(-0.02, 0.02),
                                "lng": coords[1] + random.uniform(-0.02, 0.02)
                            })
                    except: continue
            
            print(f" Progres: {len(all_data)} data terkumpul.")

        # Simpan ke CSV
        df_final = pd.DataFrame(all_data)
        df_final.to_csv("data_jabar_umkm.csv", index=False)
        print(f"Scraping Selesai Total data yang didapat: {len(df_final)}")
        driver.quit()
        return True
    except Exception as e:
        print(f"Error : {e}")
        if 'driver' in locals(): driver.quit()
        return False

if __name__ == "__main__":
    # Menjalankan dengan target 1500 data
    scrape_jabar_raya(1500)
