import math


def _center(box):
    """
    Calculate the center point of an OCR bounding box.
    """

    xs = [point[0] for point in box]
    ys = [point[1] for point in box]

    return (
        sum(xs) / len(xs),
        sum(ys) / len(ys)
    )


def _box_size(box):
    """
    Estimate width and height of an OCR bounding box.
    """

    xs = [point[0] for point in box]
    ys = [point[1] for point in box]

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    return width, height


def _box_area(box):
    width, height = _box_size(box)
    return width * height


def analyze_ocr_regions(items):
    """
    Analyze PaddleOCR text regions for basic layout anomalies.

    This does not prove document forgery.
    It identifies regions that deserve further inspection.
    """

    if not items:
        return {
            "status": "UNAVAILABLE",
            "region_count": 0,
            "suspicious_regions": 0,
            "signals": [
                {
                    "name": "OCR Regions",
                    "status": "WARNING",
                    "message": "No OCR regions were detected."
                }
            ]
        }

    valid_items = []

    for item in items:

        box = item.get("box")
        text = str(item.get("text", "")).strip()
        confidence = item.get("confidence")

        if not box or not text:
            continue

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        valid_items.append({
            "text": text,
            "confidence": confidence,
            "box": box
        })

    if not valid_items:
        return {
            "status": "UNAVAILABLE",
            "region_count": 0,
            "suspicious_regions": 0,
            "signals": [
                {
                    "name": "OCR Regions",
                    "status": "WARNING",
                    "message": "No valid OCR regions were available."
                }
            ]
        }

    signals = []
    suspicious_regions = 0

    # --------------------------------------------------
    # 1. OCR confidence distribution
    # --------------------------------------------------

    confidences = [
        item["confidence"]
        for item in valid_items
    ]

    average_confidence = (
        sum(confidences) / len(confidences)
    )

    low_confidence_count = sum(
        1
        for confidence in confidences
        if confidence < 0.60
    )

    low_confidence_ratio = (
        low_confidence_count / len(confidences)
    )

    if low_confidence_ratio > 0.30:

        signals.append({
            "name": "OCR Confidence Distribution",
            "status": "WARNING",
            "message": (
                f"{low_confidence_count} of "
                f"{len(confidences)} OCR regions have "
                f"confidence below 0.60."
            )
        })

        suspicious_regions += low_confidence_count

    else:

        signals.append({
            "name": "OCR Confidence Distribution",
            "status": "PASS",
            "message": (
                f"Average OCR confidence is "
                f"{average_confidence:.4f}."
            )
        })

    # --------------------------------------------------
    # 2. Region size analysis
    # --------------------------------------------------

    areas = [
        _box_area(item["box"])
        for item in valid_items
    ]

    median_area = sorted(areas)[len(areas) // 2]

    abnormal_size_count = 0

    for item, area in zip(valid_items, areas):

        if median_area <= 0:
            continue

        ratio = area / median_area

        if ratio > 8 or ratio < 0.125:
            abnormal_size_count += 1

    if abnormal_size_count > 0:

        signals.append({
            "name": "OCR Region Size",
            "status": "REVIEW",
            "message": (
                f"{abnormal_size_count} OCR regions have "
                f"unusually different dimensions from the "
                f"median region size."
            )
        })

        suspicious_regions += abnormal_size_count

    else:

        signals.append({
            "name": "OCR Region Size",
            "status": "PASS",
            "message": (
                "OCR region dimensions are reasonably "
                "consistent."
            )
        })

    # --------------------------------------------------
    # 3. Overlap analysis
    # --------------------------------------------------

    overlap_count = 0

    for i in range(len(valid_items)):

        box_a = valid_items[i]["box"]

        ax1 = min(point[0] for point in box_a)
        ay1 = min(point[1] for point in box_a)
        ax2 = max(point[0] for point in box_a)
        ay2 = max(point[1] for point in box_a)

        for j in range(i + 1, len(valid_items)):

            box_b = valid_items[j]["box"]

            bx1 = min(point[0] for point in box_b)
            by1 = min(point[1] for point in box_b)
            bx2 = max(point[0] for point in box_b)
            by2 = max(point[1] for point in box_b)

            overlap_width = max(
                0,
                min(ax2, bx2) - max(ax1, bx1)
            )

            overlap_height = max(
                0,
                min(ay2, by2) - max(ay1, by1)
            )

            overlap_area = (
                overlap_width *
                overlap_height
            )

            if overlap_area <= 0:
                continue

            area_a = max(
                1,
                (ax2 - ax1) * (ay2 - ay1)
            )

            area_b = max(
                1,
                (bx2 - bx1) * (by2 - by1)
            )

            smaller_area = min(
                area_a,
                area_b
            )

            overlap_ratio = (
                overlap_area / smaller_area
            )

            if overlap_ratio > 0.30:
                overlap_count += 1

    if overlap_count > 0:

        signals.append({
            "name": "OCR Region Overlap",
            "status": "REVIEW",
            "message": (
                f"{overlap_count} OCR region pairs "
                f"have significant overlap."
            )
        })

        suspicious_regions += overlap_count

    else:

        signals.append({
            "name": "OCR Region Overlap",
            "status": "PASS",
            "message": (
                "No significant OCR region overlap detected."
            )
        })

    # --------------------------------------------------
    # 4. Text positioning analysis
    # --------------------------------------------------

    centers = [
        _center(item["box"])
        for item in valid_items
    ]

    position_anomaly_count = 0

    if len(centers) >= 3:

        distances = []

        for i in range(len(centers)):

            nearest_distance = None

            for j in range(len(centers)):

                if i == j:
                    continue

                distance = math.sqrt(
                    (centers[i][0] - centers[j][0]) ** 2
                    +
                    (centers[i][1] - centers[j][1]) ** 2
                )

                if (
                    nearest_distance is None
                    or distance < nearest_distance
                ):
                    nearest_distance = distance

            if nearest_distance is not None:
                distances.append(nearest_distance)

        if distances:

            median_distance = sorted(distances)[
                len(distances) // 2
            ]

            if median_distance > 0:

                for distance in distances:

                    if distance > median_distance * 8:
                        position_anomaly_count += 1

    if position_anomaly_count > 0:

        signals.append({
            "name": "Text Positioning",
            "status": "REVIEW",
            "message": (
                f"{position_anomaly_count} OCR regions "
                f"are unusually isolated from neighboring "
                f"text regions."
            )
        })

        suspicious_regions += position_anomaly_count

    else:

        signals.append({
            "name": "Text Positioning",
            "status": "PASS",
            "message": (
                "OCR regions have reasonable spatial "
                "relationships."
            )
        })

    # --------------------------------------------------
    # Overall status
    # --------------------------------------------------

    review_count = sum(
        1
        for signal in signals
        if signal["status"] in ["WARNING", "REVIEW"]
    )

    if review_count == 0:
        overall_status = "NO OBVIOUS REGION ANOMALIES"
    elif review_count <= 2:
        overall_status = "REVIEW RECOMMENDED"
    else:
        overall_status = "REVIEW REQUIRED"

    return {
        "status": overall_status,
        "region_count": len(valid_items),
        "suspicious_regions": suspicious_regions,
        "average_confidence": round(
            average_confidence,
            4
        ),
        "signals": signals
    }