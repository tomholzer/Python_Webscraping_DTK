from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import datetime
import time
from unidecode import unidecode

def scroll_to_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView();", element)

# Nastavení Selenium
options = Options()
options.add_argument("--headless")  # Spustí prohlížeč na pozadí
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Otevření stránky
start_time = time.time()
driver.get("https://portal.desettisickroku.cz/firma/53/tymy")

# Počkání na načtení prvků
wait = WebDriverWait(driver, 20)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.flex.items-center.text-sm.font-semibold.text-gray-900")))
print(f"Načtení stránky týmů trvalo {time.time() - start_time:.2f} sekund")

# Příprava CSV souboru
now = datetime.datetime.now()
csv_filename = f"DTK_{now.year}_{now.month:02d}.csv"

header = ["Tým", "Město", "Člen"] + [str(i) for i in range(1, 31)]

with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(header)

    # Uložení odkazů na týmy
    tym_elements = driver.find_elements(By.CSS_SELECTOR, "div.flex.items-center.text-sm.font-semibold.text-gray-900")
    tym_data = []
    
    for tym in tym_elements:
        try:
            scroll_to_element(driver, tym)
            time.sleep(1)
            nazev_tymu = tym.text.strip()
            mesto = "Neznámé"
            
            mesto_element = tym.find_element(By.XPATH, "following-sibling::div")
            if mesto_element:
                mesto = mesto_element.text.strip()
            
            link_element = tym.find_element(By.XPATH, "ancestor::a")
            tym_url = link_element.get_attribute("href") if link_element else None
            
            tym_data.append((nazev_tymu, mesto, tym_url))
        except Exception:
            print(f"⚠️ Chyba při zpracování týmu: {nazev_tymu}")
            continue
    
    for nazev_tymu, mesto, tym_url in tym_data:
        print(f"🔄 Zpracovávám tým: {nazev_tymu} ({mesto})")
        
        if not tym_url:
            print(f"❌ Nelze získat odkaz na tým: {nazev_tymu}")
            continue
        
        start_team_time = time.time()
        driver.get(tym_url)
        time.sleep(2)
        print(f"✅ Načtení stránky týmu {nazev_tymu} ({time.time() - start_team_time:.2f} s)")
        
        try:
            wait.until(EC.visibility_of_element_located((By.XPATH, "//td[contains(@class, 'whitespace-nowrap')]")))
            clenove_elements = driver.find_elements(By.XPATH, "//td[contains(@class, 'whitespace-nowrap')]")
            
            clenove_data = {}
            clenove_jmena = []
            clenove_url = {}
            
            for clen in clenove_elements:
                try:
                    jmeno_element = clen.find_element(By.CSS_SELECTOR, "span.font-semibold")
                    jmeno = jmeno_element.text.strip()
                    clenove_jmena.append(jmeno)
                    
                    profil_link = clen.find_element(By.TAG_NAME, "a").get_attribute("href")
                    clenove_url[jmeno] = profil_link
                except Exception:
                    print(f"⚠️ Chyba při zpracování člena týmu {nazev_tymu}")
        except Exception:
            print(f"❌ Chyba při zpracování členů týmu {nazev_tymu}")
        
        for jmeno, profil_url in clenove_url.items():
            if not profil_url:
                print(f"❌ Nelze získat odkaz na profil člena {jmeno}")
                continue
            
            start_member_time = time.time()
            driver.get(profil_url)
            time.sleep(2)
            print(f"✅ Načtení stránky člena {jmeno} ({time.time() - start_member_time:.2f} s)")
            
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")))
                chart_instances = driver.execute_script("return Object.keys(Chart.instances)")
                
                if chart_instances:
                    graph_data = driver.execute_script(f"return Chart.instances[{chart_instances[0]}].data")
                    
                    for dataset in graph_data["datasets"]:
                        if unidecode(dataset["label"]) == unidecode(jmeno):
                            clenove_data[jmeno] = dataset["data"]
                            break
                else:
                    print(f"❌ Žádné instance grafu nenalezeny pro člena {jmeno}")
            except Exception:
                print(f"⚠️ Chyba při získávání dat z grafu člena {jmeno}")
        
        for jmeno in clenove_jmena:
            data_z_grafu = clenove_data.get(jmeno, ["0.0"] * 30)
            csv_writer.writerow([nazev_tymu, mesto, jmeno] + data_z_grafu)

# Zavření Selenium driveru
driver.quit()
print(f"🚀 Data byla uložena do {csv_filename}")
