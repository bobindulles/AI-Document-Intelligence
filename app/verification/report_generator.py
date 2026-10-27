import json
from pathlib import Path
from datetime import datetime


def generate_report(
    document_type,
    fields,
    classification,
    ml_result,
    region_result,
    forgery_result,
    verification_result,
    final_result
):

    report = {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(),
            "system": "AI Document Intelligence",
            "report_version": "1.0"
        },

        "document": {
            "document_type": document_type,
            "classification": classification
        },

        "extracted_fields": fields,

        "ocr_analysis": {
            "confidence": verification_result.get("ocr_confidence"),
            "region_status": region_result.get("status"),
            "region_count": region_result.get("region_count"),
            "suspicious_regions": region_result.get("suspicious_regions"),
            "average_confidence": region_result.get("average_confidence")
        },

        "ml_analysis": {
            "status": ml_result.get("status"),
            "prediction": ml_result.get("prediction"),
            "anomaly_score": ml_result.get("anomaly_score"),
            "features": ml_result.get("features")
        },

        "forgery_analysis": {
            "status": forgery_result.get("status"),
            "signals": forgery_result.get("signals")
        },

        "verification_analysis": {
            "status": verification_result.get("overall_status"),
            "reliability_score": verification_result.get("reliability_score"),
            "findings": verification_result.get("findings")
        },

        "final_result": {
            "overall_status": final_result.get("overall_status"),
            "document_consistency": final_result.get("document_consistency"),
            "ocr_reliability": final_result.get("ocr_reliability"),
            "visual_analysis": final_result.get("visual_analysis"),
            "ocr_region_analysis": final_result.get("ocr_region_analysis"),
            "ml_anomaly": final_result.get("ml_anomaly"),
            "ela_status": final_result.get("ela_status"),
            "explanation": final_result.get("explanation")
        }
    }

    return report


def save_report(report, output_path):

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False
        )

    return output_path