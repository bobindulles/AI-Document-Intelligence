from app.verification.ml_verifier import verify_invoice


print("\n" + "=" * 50)
print("       ML INVOICE VERIFICATION TEST")
print("=" * 50)


result = verify_invoice(
    qty=1,
    amount=150,
    invoice_date="05/09/2022"
)


print("\nML VERIFICATION RESULT")

print(f"Status        : {result['status']}")
print(f"Prediction    : {result['prediction']}")
print(f"Anomaly Score : {result['anomaly_score']:.6f}")


print("\nFeatures Used:")

for key, value in result["features"].items():
    print(f"{key:22}: {value}")


print("=" * 50)