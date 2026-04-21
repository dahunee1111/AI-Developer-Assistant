from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime

from db import (
    get_conn,
    user_exists,
    ensure_profile_custom_row,
)

router = APIRouter()


class ApplyItemRequest(BaseModel):
    user_id: int
    item_id: int


@router.get("/profile/custom")
def get_profile_custom(user_id: int = Query(...)):
    ensure_profile_custom_row(user_id)

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT upc.user_id,
               theme.item_name as theme_name, theme.style_value as theme_style,
               badge.item_name as badge_name, badge.style_value as badge_style,
               bg.item_name as background_name, bg.style_value as background_style,
               nc.item_name as name_color_name, nc.style_value as name_color_style,
               cs.item_name as card_skin_name, cs.style_value as card_skin_style,
               upc.updated_at
        FROM user_profile_custom upc
        LEFT JOIN shop_items theme ON upc.active_theme_item_id = theme.id
        LEFT JOIN shop_items badge ON upc.active_badge_item_id = badge.id
        LEFT JOIN shop_items bg ON upc.active_background_item_id = bg.id
        LEFT JOIN shop_items nc ON upc.active_name_color_item_id = nc.id
        LEFT JOIN shop_items cs ON upc.active_card_skin_item_id = cs.id
        WHERE upc.user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    return {
        "custom": {
            "user_id": user_id,
            "theme_name": row["theme_name"] if row else None,
            "theme_style": row["theme_style"] if row else None,
            "badge_name": row["badge_name"] if row else None,
            "badge_style": row["badge_style"] if row else None,
            "background_name": row["background_name"] if row else None,
            "background_style": row["background_style"] if row else None,
            "name_color_name": row["name_color_name"] if row else None,
            "name_color_style": row["name_color_style"] if row else None,
            "card_skin_name": row["card_skin_name"] if row else None,
            "card_skin_style": row["card_skin_style"] if row else None,
            "updated_at": row["updated_at"] if row else None
        }
    }


@router.post("/profile/apply-item")
def apply_profile_item(data: ApplyItemRequest):
    ensure_profile_custom_row(data.user_id)

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    cursor.execute("""
        SELECT si.id, si.item_name, si.item_type, si.style_value
        FROM user_inventory ui
        JOIN shop_items si ON ui.item_id = si.id
        WHERE ui.user_id = ? AND si.id = ?
    """, (data.user_id, data.item_id))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return {"message": "보유 중인 아이템만 적용할 수 있습니다."}

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if item["item_type"] == "theme":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_theme_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))

    elif item["item_type"] == "badge":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_badge_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))

    elif item["item_type"] == "background":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_background_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))

    elif item["item_type"] == "name_color":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_name_color_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))

    elif item["item_type"] == "card_skin":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_card_skin_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))

    else:
        conn.close()
        return {"message": "지원하지 않는 아이템 타입입니다."}

    conn.commit()
    conn.close()

    return {
        "message": f"{item['item_name']} 적용 완료",
        "item_id": data.item_id,
        "item_name": item["item_name"],
        "item_type": item["item_type"],
        "style_value": item["style_value"]
    }