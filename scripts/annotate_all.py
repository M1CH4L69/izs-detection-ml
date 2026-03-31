#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import cv2
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CLASS_MAPPINGS: Dict[str, Dict[str, str]] = {
    "hasici": {
        "car": "hasici",
        "truck": "hasici",
        "bus": "hasici",
        "motorcycle": "hasici",
    },
    "policie": {
        "car": "policie",
        "truck": "policie",
        "bus": "policie",
        "motorcycle": "policie",
    },
    "zachranka": {
        "car": "zachranka",
        "truck": "zachranka",
        "bus": "zachranka",
        "motorcycle": "zachranka",
    },
}

class ImageAnnotator:
    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        class_mapping: Optional[Dict[str, str]] = None,
    ):
        """Initialize image annotator."""
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.class_names = {}
        self.class_mapping = class_mapping if class_mapping else CLASS_MAPPINGS["other"]

        self._load_model()

    def _load_model(self):
        try:
            logger.info("Loading YOLOv8 model: %s", self.model_name)
            self.model = YOLO(self.model_name)
            self.class_names = self.model.names
            logger.info("Model loaded with %d classes", len(self.class_names))
        except Exception as exc:
            logger.error("Failed to load model: %s", exc)
            raise

    def _map_class_name(self, class_name: str) -> Optional[str]:
        return self.class_mapping.get(class_name.lower().strip())

    def annotate_image(
        self,
        image_path: str,
        save_annotated: bool = True,
        output_dir: Optional[str] = None,
    ) -> Dict:
        try:
            if not os.path.exists(image_path):
                return {"image": image_path, "detections": [], "error": "File not found"}

            results = self.model(image_path, conf=self.confidence_threshold, verbose=False)
            result = results[0]

            detections = []
            for box in result.boxes:
                class_id = int(box.cls[0])
                original_class_name = self.class_names.get(class_id, "unknown")
                mapped_class_name = self._map_class_name(original_class_name)

                if mapped_class_name is None:
                    continue

                detection = {
                    "class_id": class_id,
                    "class_name": original_class_name,
                    "class_name_mapped": mapped_class_name,
                    "confidence": float(box.conf[0]),
                    "bbox": {
                        "x_min": float(box.xyxy[0][0]),
                        "y_min": float(box.xyxy[0][1]),
                        "x_max": float(box.xyxy[0][2]),
                        "y_max": float(box.xyxy[0][3]),
                    },
                }
                detections.append(detection)

            if save_annotated:
                if output_dir is None:
                    output_dir = os.path.dirname(image_path)

                annotated_output_dir = os.path.join(output_dir, "annotated")
                os.makedirs(annotated_output_dir, exist_ok=True)

                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                annotated_path = os.path.join(annotated_output_dir, f"{name}_annotated{ext}")

                image = cv2.imread(image_path)
                if image is not None:
                    for detection in detections:
                        bbox = detection["bbox"]
                        x_min = int(bbox["x_min"])
                        y_min = int(bbox["y_min"])
                        x_max = int(bbox["x_max"])
                        y_max = int(bbox["y_max"])

                        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                        label = f"{detection['class_name_mapped']} ({detection['confidence']:.2f})"
                        cv2.putText(
                            image,
                            label,
                            (x_min, max(20, y_min - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 0),
                            2,
                        )
                    cv2.imwrite(annotated_path, image)

            return {
                "image": image_path,
                "detections": detections,
                "num_detections": len(detections),
                "error": None,
            }
        except Exception as exc:
            logger.error("Error annotating %s: %s", image_path, exc)
            return {"image": image_path, "detections": [], "error": str(exc)}

    def _save_yolo_format(
        self,
        output_dir: str,
        results: List[Dict],
        save_classes_txt: bool = True,
        sorted_classes_override: Optional[List[str]] = None,
    ) -> List[Dict]:
        labels_dir = os.path.join(output_dir, "labels")
        os.makedirs(labels_dir, exist_ok=True)

        sorted_classes = (
            sorted_classes_override
            if sorted_classes_override is not None
            else sorted(set(self.class_mapping.values()))
        )

        if save_classes_txt:
            classes_path = os.path.join(output_dir, "classes.txt")
            with open(classes_path, "w", encoding="utf-8") as handle:
                for class_name in sorted_classes:
                    handle.write(f"{class_name}\n")

        summary = []
        for result in results:
            if result.get("error") or not result.get("detections"):
                continue

            image_path = result["image"]
            image = cv2.imread(image_path)
            if image is None:
                continue

            img_height, img_width = image.shape[:2]
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            label_path = os.path.join(labels_dir, f"{image_name}.txt")

            valid = [d for d in result["detections"] if d.get("class_name_mapped")]
            if not valid:
                continue

            with open(label_path, "w", encoding="utf-8") as handle:
                for detection in valid:
                    class_idx = sorted_classes.index(detection["class_name_mapped"])
                    bbox = detection["bbox"]
                    x_min = bbox["x_min"]
                    y_min = bbox["y_min"]
                    x_max = bbox["x_max"]
                    y_max = bbox["y_max"]

                    x_center = ((x_min + x_max) / 2.0) / img_width
                    y_center = ((y_min + y_max) / 2.0) / img_height
                    width = (x_max - x_min) / img_width
                    height = (y_max - y_min) / img_height

                    x_center = max(0.0, min(1.0, x_center))
                    y_center = max(0.0, min(1.0, y_center))
                    width = max(0.0, min(1.0, width))
                    height = max(0.0, min(1.0, height))

                    handle.write(
                        f"{class_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"
                    )

            summary.append(
                {
                    "image": image_path,
                    "label_file": label_path,
                    "detections": len(valid),
                }
            )

        return summary

    def _create_dataset_structure(
        self,
        output_dir: str,
        results: List[Dict],
        save_classes_txt: bool = True,
        sorted_classes_override: Optional[List[str]] = None,
    ) -> List[Dict]:
        images_dir = os.path.join(output_dir, "images")
        labels_dir = os.path.join(output_dir, "labels")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)

        sorted_classes = (
            sorted_classes_override
            if sorted_classes_override is not None
            else sorted(set(self.class_mapping.values()))
        )

        if save_classes_txt:
            classes_path = os.path.join(output_dir, "classes.txt")
            with open(classes_path, "w", encoding="utf-8") as handle:
                for class_name in sorted_classes:
                    handle.write(f"{class_name}\n")

        summary = []
        for result in results:
            if result.get("error") or not result.get("detections"):
                continue

            valid = [d for d in result["detections"] if d.get("class_name_mapped")]
            if not valid:
                continue

            source_path = result["image"]
            image = cv2.imread(source_path)
            if image is None:
                continue

            img_height, img_width = image.shape[:2]
            image_name = os.path.basename(source_path)
            image_name_no_ext = os.path.splitext(image_name)[0]

            dest_image = os.path.join(images_dir, image_name)
            shutil.copy2(source_path, dest_image)

            label_path = os.path.join(labels_dir, f"{image_name_no_ext}.txt")
            with open(label_path, "w", encoding="utf-8") as handle:
                for detection in valid:
                    class_idx = sorted_classes.index(detection["class_name_mapped"])
                    bbox = detection["bbox"]
                    x_min = bbox["x_min"]
                    y_min = bbox["y_min"]
                    x_max = bbox["x_max"]
                    y_max = bbox["y_max"]

                    x_center = ((x_min + x_max) / 2.0) / img_width
                    y_center = ((y_min + y_max) / 2.0) / img_height
                    width = (x_max - x_min) / img_width
                    height = (y_max - y_min) / img_height

                    x_center = max(0.0, min(1.0, x_center))
                    y_center = max(0.0, min(1.0, y_center))
                    width = max(0.0, min(1.0, width))
                    height = max(0.0, min(1.0, height))

                    handle.write(
                        f"{class_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"
                    )

            summary.append(
                {
                    "image": dest_image,
                    "label_file": label_path,
                    "detections": len(valid),
                }
            )

        return summary

    def annotate_folder(
        self,
        folder_path: str,
        save_annotated: bool = True,
        output_dir: Optional[str] = None,
        save_json: bool = True,
        save_yolo: bool = True,
        create_dataset: bool = False,
        recursive: bool = False,
        skip_existing: bool = False,
        class_mapping: Optional[Dict[str, str]] = None,
        is_combined: bool = False,
        sorted_classes_override: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Annotate all images in a folder."""
        if class_mapping:
            self.class_mapping = class_mapping

        if not os.path.isdir(folder_path):
            logger.error("Folder not found: %s", folder_path)
            return []

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
        image_files = []

        if recursive:
            for ext in image_extensions:
                image_files.extend(Path(folder_path).rglob(f"*{ext}"))
                image_files.extend(Path(folder_path).rglob(f"*{ext.upper()}"))
        else:
            for ext in image_extensions:
                image_files.extend(Path(folder_path).glob(f"*{ext}"))
                image_files.extend(Path(folder_path).glob(f"*{ext.upper()}"))

        image_files = sorted(set(str(path) for path in image_files))
        if not image_files:
            logger.warning("No images found in %s", folder_path)
            return []

        if output_dir is None:
            output_dir = folder_path

        if skip_existing:
            original_count = len(image_files)
            filtered = []
            for image_file in image_files:
                filename = os.path.basename(image_file)
                stem, ext = os.path.splitext(filename)

                has_label = os.path.exists(os.path.join(output_dir, "labels", f"{stem}.txt"))
                has_annotated = os.path.exists(
                    os.path.join(output_dir, "annotated", f"{stem}_annotated{ext}")
                )

                if save_yolo and has_label:
                    continue
                if save_annotated and has_annotated:
                    continue
                filtered.append(image_file)

            image_files = filtered
            skipped = original_count - len(image_files)
            if skipped > 0:
                logger.info("Skipped %d existing images", skipped)

        if not image_files:
            logger.info("No new images to process")
            return []

        os.makedirs(output_dir, exist_ok=True)

        results = []
        for index, image_file in enumerate(image_files, start=1):
            logger.info("[%d/%d] %s", index, len(image_files), os.path.basename(image_file))
            result = self.annotate_image(
                image_file,
                save_annotated=save_annotated,
                output_dir=output_dir,
            )
            results.append(result)

        if save_json and not is_combined:
            json_path = os.path.join(output_dir, "annotations.json")
            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump(results, handle, indent=2, ensure_ascii=False)
            logger.info("Saved JSON: %s", json_path)

        if save_yolo:
            if create_dataset:
                self._create_dataset_structure(
                    output_dir,
                    results,
                    save_classes_txt=not is_combined,
                    sorted_classes_override=sorted_classes_override,
                )
            else:
                self._save_yolo_format(
                    output_dir,
                    results,
                    save_classes_txt=not is_combined,
                    sorted_classes_override=sorted_classes_override,
                )

        total_detections = sum(item.get("num_detections", 0) for item in results)
        logger.info("Processed %d images, detections: %d", len(results), total_detections)
        return results


def main():
    """CLI entry point."""
    print("\n" + "=" * 60)
    print("YOLOv8 MULTI-FOLDER IMAGE ANNOTATOR")
    print("=" * 60)

    folders_to_process = [
        (os.path.join("stahnute_obrazky", "hasici"), CLASS_MAPPINGS["hasici"]),
        (os.path.join("stahnute_obrazky", "policie"), CLASS_MAPPINGS["policie"]),
        (os.path.join("stahnute_obrazky", "zachranka"), CLASS_MAPPINGS["zachranka"]),
    ]

    existing_folders = []
    for folder, mapping in folders_to_process:
        if os.path.isdir(folder):
            existing_folders.append((folder, mapping))
        else:
            logger.warning("Folder not found: %s", folder)

    if not existing_folders:
        logger.error("No default folders found")
        manual_folder = input("Enter image folder path: ").strip()
        if manual_folder and os.path.isdir(manual_folder):
            mapping_key = input(
                "Mapping key (pid/other/hasici/policie/zachranka, default: other): "
            ).strip().lower() or "other"
            mapping = CLASS_MAPPINGS.get(mapping_key, CLASS_MAPPINGS["other"])
            existing_folders = [(manual_folder, mapping)]
        else:
            return

    output_choice = (
        input("\nSave all outputs in one combined folder? (y/n, default: y): ").strip().lower()
        != "n"
    )
    if output_choice:
        output_dir = input("Output folder (Enter = annotations_combined): ").strip()
        if not output_dir:
            output_dir = "annotations_combined"
    else:
        output_dir = None

    recursive = input("Process subfolders recursively? (y/n, default: n): ").strip().lower() == "y"
    skip_existing = input("Skip already annotated images? (y/n, default: y): ").strip().lower() != "n"

    models = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"]
    print("\nAvailable models:")
    for idx, model_name in enumerate(models, start=1):
        print(f"  {idx}. {model_name}")

    model_choice = input("Model (1-5 or custom, default: 1): ").strip()
    if model_choice.isdigit() and 1 <= int(model_choice) <= len(models):
        model_name = models[int(model_choice) - 1]
    elif model_choice:
        model_name = model_choice
    else:
        model_name = "yolov8n.pt"

    confidence_input = input("Confidence threshold 0-1 (default: 0.5): ").strip()
    try:
        confidence_threshold = float(confidence_input) if confidence_input else 0.5
        confidence_threshold = max(0.0, min(1.0, confidence_threshold))
    except ValueError:
        confidence_threshold = 0.5

    metadata_only = input(
        "Generate only metadata (JSON + YOLO labels), no annotated previews? (y/n, default: n): "
    ).strip().lower() == "y"

    if metadata_only:
        save_json = True
        save_yolo = True
        save_annotated = False
        create_dataset = False
    else:
        save_json = input("Save JSON annotations? (y/n, default: y): ").strip().lower() != "n"
        save_yolo = input("Save YOLO labels? (y/n, default: y): ").strip().lower() != "n"
        save_annotated = input("Save annotated preview images? (y/n, default: y): ").strip().lower() != "n"
        create_dataset = False
        if save_yolo:
            create_dataset = (
                input("Create dataset structure (images + labels)? (y/n, default: y): ").strip().lower()
                != "n"
            )

    try:
        annotator = ImageAnnotator(
            model_name=model_name,
            confidence_threshold=confidence_threshold,
        )

        all_results = []
        all_mapped_classes = set()
        for _, mapping in existing_folders:
            all_mapped_classes.update(mapping.values())
        global_sorted_classes = sorted(all_mapped_classes)

        for folder_path, mapping in existing_folders:
            folder_output = output_dir if output_dir else folder_path
            logger.info("Processing folder: %s", folder_path)
            results = annotator.annotate_folder(
                folder_path=folder_path,
                save_annotated=save_annotated,
                output_dir=folder_output,
                save_json=save_json,
                save_yolo=save_yolo,
                create_dataset=create_dataset,
                recursive=recursive,
                skip_existing=skip_existing,
                class_mapping=mapping,
                is_combined=bool(output_dir),
                sorted_classes_override=global_sorted_classes if output_dir else None,
            )
            all_results.extend(results)

        logger.info("Done. Total processed images: %d", len(all_results))

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            if save_json:
                combined_json = os.path.join(output_dir, "annotations.json")
                with open(combined_json, "w", encoding="utf-8") as handle:
                    json.dump(all_results, handle, indent=2, ensure_ascii=False)
                logger.info("Saved combined JSON: %s", combined_json)

            if save_yolo:
                classes_txt_path = os.path.join(output_dir, "classes.txt")
                with open(classes_txt_path, "w", encoding="utf-8") as handle:
                    for class_name in global_sorted_classes:
                        handle.write(f"{class_name}\n")
                logger.info("Saved combined classes: %s", classes_txt_path)

    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        import traceback

        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
