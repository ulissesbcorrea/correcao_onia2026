"""Image service: match students to their justification images.

gabaritos folder structure:
  gabaritos/{polo}/{student_name}_{id}/
    answer_sheet.{jpg,png}
    sheet_1.{jpg,png} ... sheet_5.{jpg,png}
"""

import os
import glob
import unicodedata

GABARITOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "gabaritos")


def normalize(s):
    """Remove accents, lowercase, strip for fuzzy matching."""
    if not s:
        return ""
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')
    return s.lower().strip()


def find_student_images(xlsx_id=None, student_name=None):
    """Find all images for a student. Matches by name (fuzzy) or xlsx_id."""
    images = []
    if not os.path.isdir(GABARITOS_DIR):
        return images

    name_norm = normalize(student_name) if student_name else ""

    for polo in os.listdir(GABARITOS_DIR):
        polo_path = os.path.join(GABARITOS_DIR, polo)
        if not os.path.isdir(polo_path):
            continue
        for folder in os.listdir(polo_path):
            folder_path = os.path.join(polo_path, folder)
            if not os.path.isdir(folder_path):
                continue

            matched = False
            # Match by xlsx_id
            if xlsx_id and f"_{xlsx_id}" in folder:
                matched = True
            # Match by name (normalized, first N chars for fuzzy)
            elif name_norm and len(name_norm) > 5:
                folder_norm = normalize(folder.rsplit("_", 1)[0])
                # Check if student name is contained in folder name or vice versa
                if name_norm in folder_norm or folder_norm in name_norm:
                    matched = True
                # Also check with first 15 chars for partial match
                elif len(name_norm) >= 15 and len(folder_norm) >= 15:
                    if name_norm[:15] == folder_norm[:15]:
                        matched = True

            if matched:
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
