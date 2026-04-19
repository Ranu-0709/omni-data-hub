"""Upload master_company CSV files to GCP bucket."""

import glob
from google.cloud import storage

# ── UPDATE THESE ──────────────────────────────────────────────
GCP_BUCKET_NAME = "your-gcp-bucket-name"
GCS_DEST_PREFIX = "landing_zone/master_company/"
LOCAL_DIR = "../data_generator/storage/landing_zone/master_company"
SERVICE_ACCOUNT_JSON = "path/to/service-account.json"  # or set GOOGLE_APPLICATION_CREDENTIALS env var
# ──────────────────────────────────────────────────────────────

def upload():
    client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_JSON)
    bucket = client.bucket(GCP_BUCKET_NAME)

    files = glob.glob(f"{LOCAL_DIR}/*.csv")
    if not files:
        print("No CSV files found in master_company.")
        return

    for fp in files:
        blob_name = GCS_DEST_PREFIX + fp.replace("\\", "/").split("/")[-1]
        bucket.blob(blob_name).upload_from_filename(fp)
        print(f"Uploaded → gs://{GCP_BUCKET_NAME}/{blob_name}")

    print(f"\nDone. {len(files)} file(s) uploaded.")

if __name__ == "__main__":
    upload()
