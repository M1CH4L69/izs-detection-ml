#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Control - Jednoduché menu pro anotaci
Spouští annotate_all.py a view_annotations.py
"""

import os
import sys
import subprocess
from pathlib import Path


class MasterControl:
    def __init__(self):
        """Inicializace"""
        self.base_dir = "stahnute_obrazky"
        self.output_dir = "annotations_combined"
        self.categories = ["hasici", "policie", "zachranka"]
        
    def clear_screen(self):
        """Vyčistí terminál"""
        os.system("cls" if os.name == "nt" else "clear")
    
    def print_banner(self):
        """Vypíše banner"""
        print("""
╔════════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║     🎯 ALL-IN-ONE ANNOTATOR - KOMPLETNÍ ANOTACE 🎯                   ║
║                                                                        ║
║     Vytváří YOLO + COCO + Labels datasety                            ║
║     Anotuje vozidla: Hasiči / Policie / Záchranka                    ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
        """)
    
    def count_images(self):
        """Počítá vstupní obrázky"""
        total = 0
        for category in self.categories:
            cat_dir = os.path.join(self.base_dir, category)
            if os.path.exists(cat_dir):
                images = list(Path(cat_dir).glob("*.[jJ][pP][gG]")) + \
                        list(Path(cat_dir).glob("*.[pP][nN][gG]")) + \
                        list(Path(cat_dir).glob("*.[bB][mM][pP]"))
                total += len(images)
        return total
    
    def count_annotations(self):
        """Počítá anotovaných obrázků"""
        # Aktualni pipeline uklada anotace do annotations_combined/.
        labels_dir = Path(self.output_dir) / "labels"
        annotated_dir = Path(self.output_dir) / "annotated"

        if labels_dir.exists():
            return len(list(labels_dir.glob("*.txt")))

        if annotated_dir.exists():
            return len(list(annotated_dir.glob("*_annotated.*")))

        return 0
    
    def print_menu(self):
        """Vypíše menu"""
        img_count = self.count_images()
        ann_count = self.count_annotations()
        
        print(f"\n📊 STATUS:")
        print(f"   Vstupní obrázky: {img_count}")
        print(f"   Anotovaných:     {ann_count}")
        print()
        
        print("┌─ HLAVNÍ FUNKCE")
        print("│")
        print("│ 1. Spustit ANOTACI ⭐              (annotate_all.py)")
        print("│    └─ Vytvoří YOLO + COCO + Labels datasety")
        print("│")
        print("│ 2. Prohlédnout VÝSLEDKY            (view_annotations.py)")
        print("│    └─ Interaktivní prohlídka anotovaných obrázků")
        print("│")
        print("├─ NASTAVENÍ")
        print("│")
        print("│ 3. Kontrola systému                (setup_yolo.py)")
        print("│")
        print("└─")
        print()
        print("0. UKONČIT")
        print()
    
    def run_script(self, script_name, description=""):
        """Spustí Python script"""
        if not os.path.exists(script_name):
            print(f"\n❌ Script nenalezen: {script_name}")
            input("Stiskněte ENTER...")
            return
        
        if description:
            print(f"\n{'='*80}")
            print(f"▶ {description}")
            print(f"{'='*80}\n")
        
        try:
            subprocess.run([sys.executable, script_name])
        except Exception as e:
            print(f"\n❌ Chyba: {e}")
        
        input("\nStiskněte ENTER pro pokračování...")
    
    def run(self):
        """Hlavní smyčka"""
        while True:
            self.clear_screen()
            self.print_banner()
            self.print_menu()
            
            choice = input("Vyberte možnost (0-3): ").strip()
            
            if choice == "0":
                print("\n👋 Ukončuji program...")
                sys.exit(0)
            
            elif choice == "1":
                self.run_script("annotate_all.py", "SPUŠTĚNÍ ANOTACE")
            
            elif choice == "2":
                self.run_script("view_annotations.py", "PROHLÍDKA VÝSLEDKŮ")
            
            elif choice == "3":
                self.run_script("setup_yolo.py", "KONTROLA SYSTÉMU")
            
            else:
                print("\n❌ Neplatná volba")
                input("Stiskněte ENTER...")


def main():
    """Hlavní funkce"""
    control = MasterControl()
    
    try:
        control.run()
    except KeyboardInterrupt:
        print("\n\n👋 Program přerušen")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
