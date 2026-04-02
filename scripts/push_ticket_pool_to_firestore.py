import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

JSON_FILE = Path("pool_1218_5.json")
SERVICE_ACCOUNT_FILE = Path("firebase-service-account.json")


def main():
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError("firebase-service-account.json 파일이 필요합니다.")

    if not JSON_FILE.exists():
        raise FileNotFoundError(f"{JSON_FILE} 파일이 없습니다.")

    cred = credentials.Certificate(str(SERVICE_ACCOUNT_FILE))
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    data = json.loads(JSON_FILE.read_text(encoding="utf-8"))

    meta = data["meta"]
    items = data["items"]

    pool_key = f'{meta["round"]}_{meta["count"]}'

    meta_ref = db.collection("ticket_pool_meta").document(pool_key)
    meta_ref.set(meta, merge=True)

    parent_ref = db.collection("ticket_pool_sets").document(pool_key)
    parent_ref.set({
        "round": meta["round"],
        "count": meta["count"],
        "status": "open"
    }, merge=True)

    batch = db.batch()
    batch_count = 0

    for item in items:
        doc_ref = parent_ref.collection("items").document(item["setId"])
        batch.set(doc_ref, item, merge=True)
        batch_count += 1

        if batch_count >= 400:
            batch.commit()
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        batch.commit()

    print(f"uploaded pool: {pool_key}, items={len(items)}")


if __name__ == "__main__":
    main()
