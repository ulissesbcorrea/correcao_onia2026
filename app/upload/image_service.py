"""Image service: match students to their justification images.

gabaritos folder structure:
  gabaritos/{polo}/{student_name}_{xlsx_id}/
    answer_sheet.{jpg,png}
    sheet_1.{jpg,png} ... sheet_5.{jpg,png}
"""

import os
import glob

GABARITOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "gabaritos")


def find_student_images(xlsx_id, student_name=None):
    """Find all images for a student by their xlsx_id.
    Returns list of dicts with {path, name, type}.
    """
    images = []
    if not os.path.isdir(GABARITOS_DIR):
        return images

    for polo in os.listdir(GABARITOS_DIR):
        polo_path = os.path.join(GABARITOS_DIR, polo)
        if not os.path.isdir(polo_path):
            continue
        for folder in os.listdir(polo_path):
            folder_path = os.path.join(polo_path, folder)
            if not os.path.isdir(folder_path):
                continue
            # Folder format: Name_ID or Name_ID_suffix
            if f"_{xlsx_id}" in folder:
                for ext in ("jpg", "jpeg", "png", "JPG", "PNG"):
                    for img in sorted(glob.glob(os.path.join(folder_path, f"*.{ext}"))):
                        name = os.path.basename(img).rsplit(".", 1)[0]
                        images.append({
                            "path": img,
                            "name": name,
                            "polo": polo,
                        })
                return images
    return images


def get_image_relative_path(absolute_path):
    """Convert absolute path to relative from gabaritos dir."""
    if absolute_path.startswith(GABARITOS_DIR):
        return absolute_path[len(GABARITOS_DIR):].lstrip("/")
    return absolute_path
