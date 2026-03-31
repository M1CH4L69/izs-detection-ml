#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validátor a prohlížeč anotovaných obrázků
Umožňuje procházet anotované obrázky a kontrolovat kvalitu anotací
"""

import cv2
import os
from pathlib import Path
import json


class AnnotationViewer:
    def __init__(self):
        """Inicializace"""
        self.ANNOTATED_DIR = "annotations_combined"
        self.LEGACY_ANNOTATED_DIR = "anotovane_obrazky"
        self.CATEGORIES = ["hasici", "policie", "zachranka"]

    def _collect_images_for_category(self, category):
        """Vrati seznam anotovanych obrazku pro kategorii (new + legacy format)."""
        # Legacy format: anotovane_obrazky/<kategorie>/*_anotovany.*
        legacy_dir = Path(self.LEGACY_ANNOTATED_DIR) / category
        if legacy_dir.exists():
            images = sorted(legacy_dir.glob("*_anotovany.*"))
            if images:
                return images

        # Aktualni format: annotations_combined/annotated/*_annotated.*
        combined_annotated_dir = Path(self.ANNOTATED_DIR) / "annotated"
        if not combined_annotated_dir.exists():
            return []

        annotations_json = Path(self.ANNOTATED_DIR) / "annotations.json"
        if not annotations_json.exists():
            # Kdyz neni JSON, vratime vsechny anotovane obrazky jako fallback.
            return sorted(combined_annotated_dir.glob("*_annotated.*"))

        try:
            with open(annotations_json, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return sorted(combined_annotated_dir.glob("*_annotated.*"))

        matched_names = set()
        for item in data:
            detections = item.get("detections", [])
            if not detections:
                continue

            has_category = any(
                det.get("class_name_mapped", "").strip().lower() == category
                for det in detections
            )
            if not has_category:
                continue

            image_path = item.get("image", "")
            image_name = Path(image_path).name
            stem = Path(image_name).stem
            suffix = Path(image_name).suffix
            matched_names.add(f"{stem}_annotated{suffix}")

        return sorted(
            path for path in combined_annotated_dir.glob("*_annotated.*") if path.name in matched_names
        )
        
    def list_annotations(self):
        """Vypíše dostupné anotace"""
        print(f"\n{'='*70}")
        print("DOSTUPNÉ ANOTOVANÉ OBRÁZKY")
        print(f"{'='*70}\n")
        
        found_any = False
        for category in self.CATEGORIES:
            images = self._collect_images_for_category(category)
            if images:
                found_any = True
                print(f"📁 {category.upper()} ({len(images)} obrázků)")
                for img in images[:5]:  # Prvnich 5
                    print(f"   • {img.name}")
                if len(images) > 5:
                    print(f"   ... a {len(images)-5} dalších")
                print()
        
        if not found_any:
            print("⚠️  Žádné anotované obrázky nenalezeny.")
            print("   Spusťte nejdřív anotátor: python annotate_all.py")
        
        print(f"{'='*70}\n")
        return found_any
    
    def view_category(self, category):
        """Prohlédne obrázky v kategorii"""
        images = self._collect_images_for_category(category)
        
        if not images:
            print(f"⚠️  Žádné anotované obrázky v kategorii: {category}")
            print("   Očekávaná cesta: annotations_combined/annotated/")
            return
        
        print(f"\n{'='*70}")
        print(f"PROHLÍŽENÍ OBRÁZKŮ: {category.upper()} ({len(images)} obrázků)")
        print(f"{'='*70}")
        print("\nOvládání:")
        print("  SPACE/N - Další obrázek")
        print("  P - Předchozí obrázek")
        print("  S - Uložit obrázek")
        print("  Q/ESC - Zpět")
        print()
        
        current_idx = 0
        
        while True:
            if current_idx < 0:
                current_idx = len(images) - 1
            elif current_idx >= len(images):
                current_idx = 0
            
            image_path = str(images[current_idx])
            image = cv2.imread(image_path)
            
            if image is None:
                print(f"❌ Nelze načíst: {images[current_idx].name}")
                current_idx += 1
                continue
            
            # Resize pro zobrazení
            height, width = image.shape[:2]
            max_width = 1200
            if width > max_width:
                scale = max_width / width
                image = cv2.resize(image, (int(width*scale), int(height*scale)))
            
            # Zobrazení
            window_name = f"{category.upper()} - {images[current_idx].name} [{current_idx+1}/{len(images)}]"
            cv2.imshow(window_name, image)
            
            key = cv2.waitKey(0) & 0xFF
            
            if key == ord('q') or key == 27:  # Q nebo ESC
                break
            elif key == ord('n') or key == 32 or key == ord(' '):  # N nebo SPACE
                current_idx += 1
            elif key == ord('p'):  # P
                current_idx -= 1
            elif key == ord('s'):  # S
                save_path = f"saved_{images[current_idx].name}"
                cv2.imwrite(save_path, image)
                print(f"✓ Uloženo: {save_path}")
        
        cv2.destroyAllWindows()
    
    def view_statistics(self):
        """Zobrazí statistiky"""
        json_path = os.path.join(self.ANNOTATED_DIR, "annotations.json")
        classes_path = os.path.join(self.ANNOTATED_DIR, "classes.txt")
        
        print(f"\n{'='*70}")
        print("STATISTIKY ANOTACE")
        print(f"{'='*70}\n")
        
        # Tridy
        if os.path.exists(classes_path):
            print("🏷️  CLASSES:")
            print("-" * 70)
            with open(classes_path, "r", encoding="utf-8") as handle:
                classes = [line.strip() for line in handle if line.strip()]
            print(", ".join(classes) if classes else "(prázdné)")
            print()

        # JSON anotace
        if os.path.exists(json_path):
            print("📊 JSON ANNOTATIONS:")
            print("-" * 70)
            try:
                with open(json_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)

                total_images = len(data)
                total_detections = sum(len(item.get("detections", [])) for item in data)
                print(f"Záznamů obrázků: {total_images}")
                print(f"Celkem detekcí:  {total_detections}\n")

                per_category = {category: 0 for category in self.CATEGORIES}
                for item in data:
                    for det in item.get("detections", []):
                        mapped = det.get("class_name_mapped", "").strip().lower()
                        if mapped in per_category:
                            per_category[mapped] += 1

                print("Detekce podle kategorie:")
                for category in self.CATEGORIES:
                    print(f"  {category:12s}: {per_category[category]:4d}")

            except Exception as e:
                print(f"❌ Chyba pri čtení JSON: {e}")
        else:
            print("⚠️  annotations.json nenalezen")
        
        print(f"\n{'='*70}\n")
    
    def validate_annotations(self):
        """Validuje anotace"""
        print(f"\n{'='*70}")
        print("VALIDACE ANOTACÍ")
        print(f"{'='*70}\n")
        
        total_images = 0
        total_size = 0
        
        for category in self.CATEGORIES:
            images = self._collect_images_for_category(category)
            total_images += len(images)

            for img_path in images:
                total_size += img_path.stat().st_size

                # Kontrola, že se obrázek dá načíst
                img = cv2.imread(str(img_path))
                if img is None:
                    print(f"❌ {category}: {img_path.name} - nelze načíst")
                else:
                    h, w = img.shape[:2]
                    size_mb = img_path.stat().st_size / (1024*1024)
                    print(f"✓ {category}: {img_path.name} ({w}x{h}, {size_mb:.1f}MB)")
        
        print(f"\n{'='*70}")
        print(f"Celkem obrázků: {total_images}")
        print(f"Celková velikost: {total_size / (1024*1024):.1f} MB")
        print(f"{'='*70}\n")
    
    def show_menu(self):
        """Zobrazí menu"""
        print(f"\n{'='*70}")
        print("PROHLÍŽEČ ANOTOVANÝCH OBRÁZKŮ")
        print(f"{'='*70}\n")
        
        print("1. Procházet obrázky - Hasiči")
        print("2. Procházet obrázky - Policie")
        print("3. Procházet obrázky - Záchranka")
        print("4. Statistiky anotace")
        print("5. Validovat anotace")
        print("6. Seznam anotovaných obrázků")
        print("0. Ukončit\n")
    
    def run(self):
        """Hlavní smyčka"""
        while True:
            self.show_menu()
            choice = input("Vyberte možnost (0-6): ").strip()
            
            if choice == "1":
                self.view_category("hasici")
            elif choice == "2":
                self.view_category("policie")
            elif choice == "3":
                self.view_category("zachranka")
            elif choice == "4":
                self.view_statistics()
            elif choice == "5":
                self.validate_annotations()
            elif choice == "6":
                self.list_annotations()
            elif choice == "0":
                print("Ukončuji...")
                break
            else:
                print("❌ Neplatná volba")


def main():
    """Hlavní funkce"""
    viewer = AnnotationViewer()
    
    try:
        viewer.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program přerušen")
    except Exception as e:
        print(f"\n❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
