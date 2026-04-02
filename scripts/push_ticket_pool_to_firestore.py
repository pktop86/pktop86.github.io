import json
import re
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

SERVICE_ACCOUNT_FILE = Path("firebase-service-account.json")
POOL_DIR = Path("generated_pools")


def init_firestore():
    cred = credentials.Certificate(str(SERVICE_ACCOUNT_FILE))
    firebase_admin.initialize_app(cred)
    return firestore.client()


def extract_round_and_count(path: Path):
    m = re.match(r"pool_(\d+)_(\d+)\.json$", path.name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def upload_one_pool(db, json_file: Path):
    data = json.loads(json_file.read_text(encoding="utf-8"))

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
    uploaded = 0

    for item in items:
        doc_ref = parent_ref.collection("items").document(item["setId"])
        batch.set(doc_ref, item, merge=True)
        batch_count += 1
        uploaded += 1

        if batch_count >= 400:
            batch.commit()
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        batch.commit()

    print(f"uploaded pool: {pool_key}, items={uploaded}")


def main():
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError("firebase-service-account.json 파일이 필요합니다.")

    if not POOL_DIR.exists():
        raise FileNotFoundError("generated_pools 폴더가 없습니다.")

    db = init_firestore()

    json_files = sorted(POOL_DIR.glob("pool_*.json"))
    if not json_files:
        raise FileNotFoundError("업로드할 pool_*.json 파일이 없습니다.")

    parsed = []
    for f in json_files:
        rc = extract_round_and_count(f)
        if rc:
            parsed.append((f, rc[0], rc[1]))

    if not parsed:
        raise FileNotFoundError("회차 정보를 읽을 수 있는 pool_*.json 파일이 없습니다.")

    latest_round = max(x[1] for x in parsed)
    latest_files = [x[0] for x in parsed if x[1] == latest_round]

    print(f"latest round detected = {latest_round}")
    print("files to upload:")
    for f in latest_files:
        print(" -", f)

    for json_file in sorted(latest_files):
        upload_one_pool(db, json_file)


if __name__ == "__main__":
    main()
