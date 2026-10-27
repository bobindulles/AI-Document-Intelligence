from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def analyze_image_quality(image_path):
    """
    Analyze basic image-quality properties.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Document image not found: {image_path}"
        )

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(
            f"Unable to read document image: {image_path}"
        )

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    sharpness = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    signals = []

    # Resolution
    if width * height < 500_000:
        signals.append({
            "name": "Image Resolution",
            "status": "WARNING",
            "message": (
                f"Document resolution is relatively low "
                f"({width} x {height})."
            )
        })
    else:
        signals.append({
            "name": "Image Resolution",
            "status": "PASS",
            "message": (
                f"Document resolution is sufficient "
                f"({width} x {height})."
            )
        })

    # Sharpness
    if sharpness < 50:
        signals.append({
            "name": "Image Sharpness",
            "status": "WARNING",
            "message": (
                f"Image appears blurry or low-detail "
                f"(sharpness={sharpness:.2f})."
            )
        })
    else:
        signals.append({
            "name": "Image Sharpness",
            "status": "PASS",
            "message": (
                f"Image sharpness is sufficient "
                f"(sharpness={sharpness:.2f})."
            )
        })

    # Brightness
    if brightness < 40:
        signals.append({
            "name": "Brightness",
            "status": "WARNING",
            "message": (
                f"Document image is unusually dark "
                f"(brightness={brightness:.2f})."
            )
        })
    elif brightness > 254:
        signals.append({
            "name": "Brightness",
            "status": "WARNING",
            "message": (
                f"Document image is nearly pure white "
                f"(brightness={brightness:.2f})."
            )
        })
    else:
        signals.append({
            "name": "Brightness",
            "status": "PASS",
            "message": (
                f"Document brightness is within a normal "
                f"range (brightness={brightness:.2f})."
            )
        })

    # Contrast
    if contrast < 15:
        signals.append({
            "name": "Image Contrast",
            "status": "WARNING",
            "message": (
                f"Image has unusually low contrast "
                f"(contrast={contrast:.2f})."
            )
        })
    else:
        signals.append({
            "name": "Image Contrast",
            "status": "PASS",
            "message": (
                f"Image contrast is sufficient "
                f"(contrast={contrast:.2f})."
            )
        })

    return {
        "width": width,
        "height": height,
        "sharpness": round(float(sharpness), 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "signals": signals
    }


def analyze_ela(image_path):
    """
    Perform Error Level Analysis (ELA).

    ELA works by recompressing an image and measuring
    differences between the original and recompressed image.

    Higher local differences may indicate regions that
    deserve further investigation.

    ELA is a forensic signal, not proof of forgery.
    """

    image_path = Path(image_path)

    try:
        original = Image.open(image_path).convert("RGB")
    except Exception as error:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": f"ELA could not be performed: {error}"
        }

    # ELA is most meaningful for JPEG images.
    if image_path.suffix.lower() not in [".jpg", ".jpeg"]:
        return {
            "status": "LIMITED",
            "score": None,
            "message": (
                "ELA is limited because the current document "
                "is not a JPEG image. Compression-based analysis "
                "may not represent the original document history."
            )
        }

    quality = 90

    temp_path = image_path.parent / "_ela_temp.jpg"

    try:
        original.save(
            temp_path,
            "JPEG",
            quality=quality
        )

        recompressed = Image.open(temp_path).convert("RGB")

        difference = ImageChops.difference(
            original,
            recompressed
        )

        extrema = difference.getextrema()

        max_difference = max(
            channel_max
            for _, channel_max in extrema
        )

        if max_difference == 0:
            ela_score = 0.0
        else:
            scale = 255.0 / max_difference

            enhanced = ImageEnhance.Brightness(
                difference
            ).enhance(scale)

            ela_array = np.asarray(
                enhanced,
                dtype=np.float32
            )

            ela_score = float(
                np.mean(ela_array)
            )

        if ela_score < 10:
            status = "PASS"
            message = (
                f"ELA differences are relatively low "
                f"(score={ela_score:.2f})."
            )

        elif ela_score < 25:
            status = "REVIEW"
            message = (
                f"ELA detected moderate compression differences "
                f"(score={ela_score:.2f})."
            )

        else:
            status = "WARNING"
            message = (
                f"ELA detected relatively strong compression "
                f"differences (score={ela_score:.2f}). "
                f"Further inspection is recommended."
            )

        return {
            "status": status,
            "score": round(ela_score, 2),
            "message": message
        }

    except Exception as error:

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": f"ELA analysis failed: {error}"
        }

    finally:

        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def detect_forgery_signals(image_path):
    """
    Combine image-quality analysis and ELA into
    a basic forgery-signal report.
    """

    quality_result = analyze_image_quality(image_path)

    ela_result = analyze_ela(image_path)

    signals = quality_result["signals"]

    signals.append({
        "name": "ELA Analysis",
        "status": ela_result["status"],
        "message": ela_result["message"]
    })

    warning_count = sum(
        1
        for signal in signals
        if signal["status"] in ["WARNING", "REVIEW"]
    )

    if warning_count == 0:
        overall_status = "NO OBVIOUS IMAGE ANOMALIES"

    elif warning_count <= 2:
        overall_status = "REVIEW RECOMMENDED"

    else:
        overall_status = "REVIEW REQUIRED"

    return {
        "status": overall_status,
        "image_width": quality_result["width"],
        "image_height": quality_result["height"],
        "sharpness": quality_result["sharpness"],
        "brightness": quality_result["brightness"],
        "contrast": quality_result["contrast"],
        "ela_score": ela_result["score"],
        "signals": signals
    }