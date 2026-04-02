import os
import json
import base64
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_PATH = os.path.join(ROOT_DIR, "store-stats.json")


def load_service_account_from_env():
    """
    GitHub Secrets에 넣어둔 base64 인코딩된 Firebase 서비스 계정 JSON을 읽어온다.
    Secret 이름 예시:
      FIREBASE_SERVICE_ACCOUNT_B64
    """
    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64", "").strip()
    if not b64:
        raise RuntimeError("Missing FIREBASE_SERVICE_ACCOUNT_B64 secret")

    raw = base64.b64decode(b64).decode("utf-8")
    return json.loads(raw)


def init_firestore():
    if not firebase_admin._apps:
        service_account_info = load_service_account_from_env()
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def safe_int(v, default=0):
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def safe_str(v, default=""):
    if v is None:
        return default
    return str(v).strip()


def norm_text(s: str) -> str:
    s = safe_str(s).lower()
    replacements = {
        "특별시": "시",
        "광역시": "시",
        "자치시": "시",
        "경상남도": "경남",
        "경상북도": "경북",
        "전라남도": "전남",
        "전라북도": "전북",
        "충청남도": "충남",
        "충청북도": "충북",
        "강원특별자치도": "강원",
        "제주특별자치도": "제주",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)

    for ch in [" ", "\t", "\n", "\r", "(", ")", "-", "_", ".", ",", "·", "/"]:
        s = s.replace(ch, "")

    return s


def transform_doc(doc_id, data):
    """
    앱의 normalizeLuckyStat()가 쓰기 쉬운 구조로 맞춘다.
    Firestore 필드명이 조금 달라도 최대한 흡수하도록 작성.
    """
    name = (
        safe_str(data.get("name"))
        or safe_str(data.get("shopName"))
        or safe_str(data.get("storeName"))
    )

    addr = (
        safe_str(data.get("addr"))
        or safe_str(data.get("address"))
        or safe_str(data.get("roadAddress"))
    )

    first_auto = (
        data.get("firstAutoCount")
        if data.get("firstAutoCount") is not None
        else data.get("first_auto_count")
    )
    first_manual = (
        data.get("firstManualCount")
        if data.get("firstManualCount") is not None
        else data.get("first_manual_count")
    )
    second_count = (
        data.get("secondCount")
        if data.get("secondCount") is not None
        else data.get("second_count")
    )
    recent_win_round = (
        data.get("recentWinRound")
        if data.get("recentWinRound") is not None
        else data.get("recent_round")
    )
    lucky_score = (
        data.get("luckyScore")
        if data.get("luckyScore") is not None
        else data.get("score")
    )

    item = {
        "_id": doc_id,
        "name": name,
        "addr": addr,
        "nameNorm": norm_text(name),
        "addrNorm": norm_text(addr),
        "firstAutoCount": safe_int(first_auto, 0),
        "firstManualCount": safe_int(first_manual, 0),
        "secondCount": safe_int(second_count, 0),
        "recentWinRound": safe_int(recent_win_round, 0),
        "luckyScore": safe_int(lucky_score, 0),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }

    if not item["name"]:
        return None
    return item


def main():
    db = init_firestore()

    docs = db.collection("store_stats").stream()
    items = []

    for doc in docs:
        data = doc.to_dict() or {}
        transformed = transform_doc(doc.id, data)
        if transformed:
            items.append(transformed)

    items.sort(
        key=lambda x: (
            -safe_int(x.get("luckyScore"), 0),
            -safe_int(x.get("firstAutoCount"), 0),
            -safe_int(x.get("firstManualCount"), 0),
            -safe_int(x.get("secondCount"), 0),
            x.get("name", "")
        )
    )

    payload = {
        "meta": {
            "source": "firestore:store_stats",
            "count": len(items),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        },
        "items": items,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"store-stats.json updated: {len(items)} items")


if __name__ == "__main__":
    main()
