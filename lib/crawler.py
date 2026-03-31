#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pokročilý Web Crawler pro TECHNIKAIZS.cz
Stahuje VŠECHNY obrázky vozidel IZS - BEZ LIMITŮ
Automaticky procházíí všechny stránky v každé kategorii
Rozděluje fotky do složek: hasiči, policie, záchranka
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Konfigurace
BASE_URL = "https://www.technikaizs.cz"
OUTPUT_DIR = "stahnute_obrazky"

# Kategorie a jejich URL
CATEGORIES = {
    "hasici": f"{BASE_URL}/slozka/hasici/",
    "policie": f"{BASE_URL}/slozka/policie/",
    "zachranka": f"{BASE_URL}/slozka/zachranna-sluzba/"
}

# Vytvoření session se retry mechanismem
def create_session():
    """Vytvoří session s retry mechanimem"""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(500, 502, 504, 429)
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    return session

def create_output_dirs():
    """Vytvoří výstupní složky"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for category in CATEGORIES.keys():
        category_dir = os.path.join(OUTPUT_DIR, category)
        os.makedirs(category_dir, exist_ok=True)
    print(f"✓ Vytvořeny adresáře v: {os.path.abspath(OUTPUT_DIR)}\n")

def get_next_page_url(soup, current_url):
    """Najde URL na další stranu z HTML"""
    # Hledáme odkaz "Další" nebo "Next" nebo "page/X"
    nav = soup.find('nav', class_=['navigation', 'posts-navigation'])
    if nav:
        next_link = nav.find('a', class_=['next', 'next-posts-link'])
        if next_link:
            href = next_link.get('href')
            if href:
                return urljoin(BASE_URL, href)
    
    # Alternativní metoda - hledání čísla stránky v URL
    if '/page/' in current_url:
        # Máme paginaci - zkusíme zvýšit číslo
        parts = current_url.split('/page/')
        if len(parts) == 2:
            page_part = parts[1].rstrip('/').split('/')[0]
            try:
                page_num = int(page_part)
                next_page = page_num + 1
                base_url = parts[0].rstrip('/') + '/'
                return f"{base_url}page/{next_page}/"
            except:
                pass
    else:
        # První strana - zkusíme page/2/
        base_url = current_url.rstrip('/') + '/'
        return f"{base_url}page/2/"
    
    return None

def get_article_links(soup, category_url):
    """Extrahuje všechny odkazy na články/techniku ze stránky"""
    article_links = set()
    
    # Metoda 1: Hledáme články/posts
    articles = soup.find_all('article')
    for article in articles:
        # Hledáme link uvnitř artiklu
        first_link = article.find('a', href=True)
        if first_link:
            href = first_link.get('href', '')
            if href and '/technika/' in href:
                article_links.add(urljoin(BASE_URL, href))
    
    # Metoda 2: Přímé vyhledání odkazů na techniku
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        href = link.get('href', '')
        if '/technika/' in href:
            article_links.add(urljoin(BASE_URL, href))
    
    return list(article_links)

def extract_all_images_from_page(soup):
    """Extrahuje ALL obrázky ze stránky"""
    images = set()
    
    # Hledáme všechny <img> tagy
    all_imgs = soup.find_all('img')
    for img in all_imgs:
        src = img.get('src')
        # Zkusíme i data-src pro lazy loading
        if not src:
            src = img.get('data-src')
        if not src:
            src = img.get('data-lazy-src')
        
        if src and ('wp-content' in src or 'technikaizs' in src):
            # Odstraníme parametry z URL (velikost, etc.)
            img_url = src.split('?')[0]
            images.add(urljoin(BASE_URL, img_url))
    
    # Hledáme obrázky v lankovém formátu srcset
    for img in all_imgs:
        srcset = img.get('srcset')
        if srcset:
            # Rozdělíme srcset na jednotlivé URLs
            for src_part in srcset.split(','):
                url = src_part.split()[0]
                if url and ('wp-content' in url or 'technikaizs' in url):
                    images.add(urljoin(BASE_URL, url))
    
    return list(images)

def download_image(session, image_url, category, counter):
    """Stáhne jeden obrázek"""
    try:
        response = session.get(image_url, timeout=15)
        response.raise_for_status()
        
        # Získání jména souboru
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)
        
        # Zpracování chybějícího rozšíření
        if not filename or '.' not in filename:
            ext = '.jpg'
            content_type = response.headers.get('content-type', 'image/jpeg')
            if 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            filename = f"obr_{counter:06d}{ext}"
        
        filepath = os.path.join(OUTPUT_DIR, category, filename)
        
        # Kontrola délky cesty pro Windows
        if len(filepath) > 240:
            _, ext = os.path.splitext(filename)
            filename = f"obr_{counter:06d}{ext}"
            filepath = os.path.join(OUTPUT_DIR, category, filename)
        
        # Kontrola na duplikáty
        if os.path.exists(filepath):
            return False, filename, 0  # Duplikát
        
        # Zápis souboru
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return True, filename, len(response.content)
        
    except Exception as e:
        return False, None, 0

def crawl_category_unlimited(session, category_name, category_url, max_images=1200):
    """
    Crawluje kategorii s LIMITKEM
    Stahuje až max_images obrázků
    """
    print(f"\n{'='*70}")
    print(f"📂 KATEGORIE: {category_name.upper()}")
    print(f"{'='*70}")
    print(f"Počáteční URL: {category_url}")
    print(f"LIMIT: {max_images} obrázků\n")
    
    session_used = session
    downloaded_total = 0
    total_size = 0
    skipped = 0
    current_page_url = category_url
    page_num = 1
    image_counter = 1
    max_consecutive_empty = 3  # Max. po sobě jdoucích prázdných stran
    empty_pages = 0
    processed_images = set()  # Aby jsme se vyhnuli duplikátům
    
    while True:
        print(f"[Strana {page_num}] {current_page_url}")
        
        try:
            response = session_used.get(current_page_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Získáme odkazy na články
            article_links = get_article_links(soup, current_page_url)
            print(f"  └─ Nalezeno {len(article_links)} článků")
            
            page_images = 0
            
            # Procházíme každý článek
            for idx, article_url in enumerate(article_links, 1):
                try:
                    article_response = session_used.get(article_url, timeout=15)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    
                    # Extrahujeme VŠECHNY obrázky z článku
                    images = extract_all_images_from_page(article_soup)
                    
                    for img_url in images:
                        # Kontrola duplikátů
                        if img_url in processed_images:
                            skipped += 1
                            continue
                        
                        processed_images.add(img_url)
                        success, filename, size = download_image(
                            session_used, img_url, category_name, image_counter
                        )
                        
                        if success:
                            downloaded_total += 1
                            total_size += size
                            page_images += 1
                            image_counter += 1
                            
                            # Kontrola limitu
                            if downloaded_total >= max_images:
                                print(f"\n  ✓ LIMIT {max_images} OBRÁZKŮ DOSAŽEN!")
                                break
                            
                            # Statusový řádek
                            if downloaded_total % 10 == 0:
                                print(f"  ✓ Staženého: {downloaded_total}/{max_images} | "
                                      f"Velikost: {total_size / (1024*1024):.1f} MB")
                    
                    time.sleep(0.1)  # Malá pauza mezi články
                    
                    # Kontrola limitu - pokud jsme na limitu, skončíme
                    if downloaded_total >= max_images:
                        break
                    
                except Exception as e:
                    print(f"  ✗ Chyba při zpracování článku: {e}")
                    continue
            
            # Pokud jsme stáhli obrázky, resetujeme počítadlo prázdných
            if page_images > 0:
                empty_pages = 0
                print(f"  ✓ Strana hotová: +{page_images} obrázků")
            else:
                empty_pages += 1
                print(f"  ⚠ Žádné obrázky na této straně ({empty_pages}/{max_consecutive_empty})")
                if empty_pages >= max_consecutive_empty:
                    print(f"  → Žádné nové obrázky v posledních {max_consecutive_empty} stránkách")
                    break
            
            # KONTROLA LIMITU - Pokud jsme dosáhli limitu, končíme
            if downloaded_total >= max_images:
                print(f"\n  ✓✓✓ LIMIT {max_images} OBRÁZKŮ PRO TUTO KATEGORII DOSAŽEN!")
                break
            
            # Hledáme odkaz na další stranu
            next_page = get_next_page_url(soup, current_page_url)
            
            if not next_page:
                print(f"\n  ✓ Konec paginace dosaženo")
                break
            
            current_page_url = next_page
            page_num += 1
            time.sleep(0.5)  # Pauza mezi stránkami
            
        except requests.RequestException as e:
            print(f"  ✗ Chyba při čtení stránky: {e}")
            break
        except Exception as e:
            print(f"  ✗ Neočekávaná chyba: {e}")
            break
    
    print(f"\n{'─'*70}")
    print(f"SHRNUTÍ '{category_name.upper()}':")
    print(f"  Celkem obrázků: {downloaded_total}")
    print(f"  Přeskočeno (duplikáty): {skipped}")
    print(f"  Velikost: {total_size / (1024*1024):.1f} MB")
    print(f"{'─'*70}\n")
    
    return downloaded_total, total_size

def main():
    """Hlavní funkce"""
    print("\n" + "="*70)
    print("WEB CRAWLER - TECHNIKAIZS.CZ")
    print("Stahování obrázků vozidel IZS - LIMIT 1200 NA KATEGORII")
    print("="*70 + "\n")
    
    # Vytvořit adresáře
    create_output_dirs()
    
    # Vytvořit session
    session = create_session()
    
    total_downloaded = 0
    total_size = 0
    
    try:
        # Procházíme každou kategorii (BEZ HASIČU!)
        categories_to_crawl = {
            # "hasici": CATEGORIES["hasici"],  # Přeskočit, máme dost!
            "policie": CATEGORIES["policie"],
            "zachranka": CATEGORIES["zachranka"]
        }
        
        for category_name, category_url in categories_to_crawl.items():
            downloaded, size = crawl_category_unlimited(session, category_name, category_url, max_images=1200)
            total_downloaded += downloaded
            total_size += size
            time.sleep(2)  # Pauza mezi kategoriemi
    
    finally:
        session.close()
    
    # Finální shrnutí
    print("="*70)
    print("FINÁLNÍ STATISTIKA")
    print("="*70)
    print(f"✓ CELKEM STAŽENÉHO: {total_downloaded} obrázků")
    print(f"✓ CELKOVÁ VELIKOST: {total_size / (1024*1024):.1f} MB")
    print(f"✓ VÝSTUPNÍ ADRESÁŘ: {os.path.abspath(OUTPUT_DIR)}\n")
    
    # Statistika po kategorií
    for category_name in CATEGORIES.keys():
        category_dir = os.path.join(OUTPUT_DIR, category_name)
        if os.path.exists(category_dir):
            files = os.listdir(category_dir)
            file_count = len(files)
            if file_count > 0:
                dir_size = sum(
                    os.path.getsize(os.path.join(category_dir, f))
                    for f in files
                    if os.path.isfile(os.path.join(category_dir, f))
                )
                print(f"  📁 {category_name.upper():15} {file_count:6} obrázků  │  "
                      f"{dir_size / (1024*1024):8.1f} MB")
    
    print("="*70)
    print("✓ CRAWLING HOTOVÝ!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
