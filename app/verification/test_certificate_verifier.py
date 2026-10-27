from app.verification.certificate_verifier import verify_certificate


certificate_fields = {
    "title": "COURSE COMPLETION CERTIFICATE",
    "organization": "AMITY UNIVERSITY ONLINE",
    "recipient": "PRAVEEN KUMAR",
    "course": "Analytics for Decision Making",
    "certificate_id": "XQlGWFrpUl",
    "verification_code": "XQlGWFrpUl",
    "verification_url": (
        "https://swayamplus.amigolms.com/"
        "mod/customcert/verify_certificate.php"
        "?code=XQlGWFrpUl"
    ),
    "signature": "MAganwer",
    "role": "Authorized Signatory"
}


result = verify_certificate(
    certificate_fields,
    ocr_confidence=0.9961
)


print("\n" + "=" * 60)
print("CERTIFICATE VERIFICATION")
print("=" * 60)

print(
    "Overall Status    :",
    result["overall_status"]
)

print(
    "Consistency Score :",
    f'{result["consistency_score"]}%'
)

print(
    "Passed Checks     :",
    result["passed_checks"]
)

print(
    "Warnings          :",
    result["warning_checks"]
)

print(
    "Failed Checks     :",
    result["failed_checks"]
)

print("\nFindings:")

for finding in result["findings"]:

    print(
        f'[{finding["status"]}] '
        f'{finding["name"]} : '
        f'{finding["message"]}'
    )

print("=" * 60)