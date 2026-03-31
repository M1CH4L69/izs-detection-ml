#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup skript - Instalace a konfigurace YOLOv8 anotace
Ověřuje requirements a pomáhá s instalací
"""

import subprocess
import sys
import os
import platform


def print_header():
    """Vypíše header"""
    print("\n" + "="*70)
    print("SETUP - YOLOv8 ANOTACE VOZIDEL")
    print("="*70 + "\n")


def check_python_version():
    """Kontroluje Python verzi"""
    print("Kontrola Python verze...")
    version = sys.version_info
    min_version = (3, 6)
    
    if version >= min_version:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} - Vyžadujeme Python {min_version[0]}.{min_version[1]}+")
        return False


def check_pip():
    """Kontroluje pip"""
    print("Kontrola pip...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ pip nalezen: {result.stdout.strip()}")
            return True
        else:
            print("❌ pip nenalezen")
            return False
    except Exception as e:
        print(f"❌ Chyba pri kontrole pip: {e}")
        return False


def install_requirements():
    """Instaluje requirements"""
    print("\nInstalace závislostí z requirements.txt...")
    
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                              capture_output=False, text=True)
        if result.returncode == 0:
            print("\n✓ Všechny závislosti nainstalovány")
            return True
        else:
            print("\n❌ Chyba pri instalaci")
            return False
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return False


def check_installed_packages():
    """Kontroluje nainstalované balíčky"""
    print("\nKontrola nainstalovaných balíčků...")
    
    required_packages = [
        "ultralytics",
        "opencv-python",
        "torch",
        "numpy"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            print(f"❌ {package} - CHYBÍ")
            missing.append(package)
    
    return len(missing) == 0, missing


def check_directories():
    """Kontroluje adresáře"""
    print("\nKontrola adresářů...")
    
    dirs_to_check = {
        "stahnute_obrazky": "Vstupní obrázky (z crawleru)",
        "stahnute_obrazky/hasici": "Obrázky hasičů",
        "stahnute_obrazky/policie": "Obrázky policie",
        "stahnute_obrazky/zachranka": "Obrázky záchranky"
    }
    
    missing_dirs = []
    for dir_path, description in dirs_to_check.items():
        if os.path.exists(dir_path):
            # Počítej obrázky
            image_count = len([f for f in os.listdir(dir_path) 
                            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))])
            print(f"✓ {dir_path} ({image_count} obrázků) - {description}")
        else:
            print(f"⚠️  {dir_path} - CHYBÍ ({description})")
            missing_dirs.append(dir_path)
    
    return missing_dirs


def check_scripts():
    """Kontroluje hlavní skripty"""
    print("\nKontrola skriptů...")
    
    required_scripts = [
        "yolo_annotator.py",
        "yolo_advanced_organizer.py",
        "run_yolo_annotation.py",
        "view_annotations.py"
    ]
    
    for script in required_scripts:
        if os.path.exists(script):
            print(f"✓ {script}")
        else:
            print(f"❌ {script} - CHYBÍ")


def system_info():
    """Vypíše info o systému"""
    print("\nInformace o systému:")
    print(f"  Operační systém: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Architektura: {platform.machine()}")


def show_quick_start():
    """Vypíše quick start"""
    print("\n" + "="*70)
    print("QUICK START")
    print("="*70 + "\n")
    
    print("1. SPUŠTĚNÍ ANOTACE:")
    print("   python run_yolo_annotation.py")
    print()
    
    print("2. NEBO PŘÍMO:")
    print("   python yolo_annotator.py")
    print("   python yolo_advanced_organizer.py")
    print()
    
    print("3. PROHLÍŽENÍ ANOTACÍ:")
    print("   python view_annotations.py")
    print()
    
    print("4. DOKUMENTACE:")
    print("   Otevřete: YOLO_ANNOTATION_README.md")
    print()


def main():
    """Hlavní funkce"""
    print_header()
    
    print("KONTROLA SYSTÉMU A KONFIGURACE\n")
    
    # Kontroly
    checks_passed = True
    
    # Python verze
    if not check_python_version():
        checks_passed = False
    
    # pip
    if not check_pip():
        checks_passed = False
        return
    
    # Kontrola adresářů
    missing_dirs = check_directories()
    
    # Kontrola skriptů
    check_scripts()
    
    # Systém info
    system_info()
    
    # Nainstalované balíčky
    print("\nKontrola nainstalovaných balíčků...")
    all_installed, missing = check_installed_packages()
    
    if not all_installed:
        print(f"\n⚠️  Chybí balíčky: {', '.join(missing)}")
        response = input("\nChcete je nyní nainstalovat? (y/n): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            if install_requirements():
                # Kontrola znovu
                all_installed, missing = check_installed_packages()
                if all_installed:
                    print("\n✓ Všechny balíčky nyní nainstalovány!")
                else:
                    print(f"\n⚠️  Některé balíčky se nepodařilo nainstalovat")
            else:
                print("\n❌ Instalace selhala")
        else:
            print("Přesvědčte se, že máte nainstalovány všechny balíčky.")
    else:
        print("✓ Všechny balíčky nainstalovány")
    
    # Varování
    if missing_dirs:
        print(f"\n⚠️  VAROVÁNÍ: Chybí następující adresáře:")
        for d in missing_dirs:
            print(f"   - {d}")
        print("\nSpusťte nejdřív web crawler:")
        print("   python lib/crawler.py")
    
    # Finální shrnutí
    print("\n" + "="*70)
    print("SHRNUTÍ")
    print("="*70)
    
    if checks_passed and all_installed and not missing_dirs:
        print("\n✓ VŠECHNY KONTROLY PROŠLY!")
        print("Můžete nyní spustit anotátor.")
    elif checks_passed and all_installed:
        print("\n⚠️  KONTROLY PROŠLY, ale chybí vstupní data.")
        print("Spusťte web crawler: python lib/crawler.py")
    else:
        print("\n❌ NĚCO NENÍ V POŘÁDKU")
        print("Vypravte problémy výše a zkuste znovu.")
    
    show_quick_start()
    
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup přerušen")
    except Exception as e:
        print(f"\n❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()
