from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime

try:
    from backend.db import (
        get_conn,
        user_exists,
        get_total_points,
        spend_points,
    )
except ImportError:
    from db import (
        get_conn,
        user_exists,
        get_total_points,
        spend_points,
    )

router = APIRouter()


class PurchaseItemRequest(BaseModel):
    user_id: int
    item_id: int


@router.get("/shop/items")
def get_shop_items(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, item_key, item_name, item_type, price, description, style_value, is_active
        FROM shop_items
        WHERE is_active = 1
        ORDER BY item_type, price ASC, id ASC
    """)
    items = cursor.fetchall()

    cursor.execute("""
        SELECT item_id
        FROM user_inventory
        WHERE user_id = ?
    """, (user_id,))
    owned_rows = cursor.fetchall()
    owned_ids = {row["item_id"] for row in owned_rows}

    conn.close()

    return {
        "items": [
            {
                "id": row["id"],
                "item_key": row["item_key"],
                "item_name": row["item_name"],
                "item_type": row["item_type"],
                "price": row["price"],
                "description": row["description"],
                "style_value": row["style_value"],
                "is_owned": row["id"] in owned_ids
            }
            for row in items
        ],
        "total_points": get_total_points(user_id)
    }


@router.post("/shop/purchase")
def purchase_shop_item(data: PurchaseItemRequest):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    cursor.execute("""
        SELECT id, item_name, item_type, price
        FROM shop_items
        WHERE id = ? AND is_active = 1
    """, (data.item_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return {"message": "구매할 아이템을 찾을 수 없습니다."}

    cursor.execute("""
        SELECT id
        FROM user_inventory
        WHERE user_id = ? AND item_id = ?
    """, (data.user_id, data.item_id))
    already_owned = cursor.fetchone()

    if already_owned:
        conn.close()
        return {
            "message": "이미 보유 중인 아이템입니다.",
            "total_points": get_total_points(data.user_id)
        }

    price = item["price"]
    if get_total_points(data.user_id) < price:
        conn.close()
        return {
            "message": "포인트가 부족합니다.",
            "total_points": get_total_points(data.user_id)
        }

    purchased_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO user_inventory (user_id, item_id, purchased_at)
        VALUES (?, ?, ?)
    """, (data.user_id, data.item_id, purchased_at))
    conn.commit()
    conn.close()

    spend_points(data.user_id, price, f"상점 구매: {item['item_name']}")

    return {
        "message": f"{item['item_name']} 구매 완료",
        "item_id": data.item_id,
        "item_name": item["item_name"],
        "item_type": item["item_type"],
        "spent_points": price,
        "total_points": get_total_points(data.user_id)
    }


@router.get("/shop/inventory")
def get_user_inventory(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ui.id as inventory_id, si.id as item_id, si.item_key, si.item_name, si.item_type,
               si.price, si.description, si.style_value, ui.purchased_at
        FROM user_inventory ui
        JOIN shop_items si ON ui.item_id = si.id
        WHERE ui.user_id = ?
        ORDER BY ui.id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "items": [
            {
                "inventory_id": row["inventory_id"],
                "item_id": row["item_id"],
                "item_key": row["item_key"],
                "item_name": row["item_name"],
                "item_type": row["item_type"],
                "price": row["price"],
                "description": row["description"],
                "style_value": row["style_value"],
                "purchased_at": row["purchased_at"]
            }
            for row in rows
        ],
        "total_points": get_total_points(user_id)
    }
