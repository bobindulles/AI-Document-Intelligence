from pathlib import Path
import pandas as pd


# Backend reference dataset
DATA_PATH = Path(r"C:\Users\MicroSoft\Downloads\invoices.csv")


def load_reference_data():
    """
    Load the backend invoice reference dataset.
    """

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Reference dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "product_id",
        "stock_code"
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns in CSV: {missing}"
        )

    return df


def get_product_frequency(df, product_id):
    """
    Count how many times a product_id appears
    in the reference dataset.
    """

    if product_id is None:
        return None

    product_id = str(product_id).strip()

    if not product_id:
        return None

    values = df["product_id"].astype(str).str.strip()

    return int((values == product_id).sum())


def get_stock_frequency(df, stock_code):
    """
    Count how many times a stock_code appears
    in the reference dataset.
    """

    if stock_code is None:
        return None

    stock_code = str(stock_code).strip()

    if not stock_code:
        return None

    values = df["stock_code"].astype(str).str.strip()

    return int((values == stock_code).sum())


def get_reference_features(product_id=None, stock_code=None):
    """
    Get reference-data features required by the ML model.
    """

    df = load_reference_data()

    product_frequency = get_product_frequency(
        df,
        product_id
    )

    stock_frequency = get_stock_frequency(
        df,
        stock_code
    )

    return {
        "product_frequency": product_frequency,
        "stock_frequency": stock_frequency
    }