from http.client import HTTPException
import uuid
from sqlalchemy.orm import Session
from models.client import Client


def split_contact_person(contact_person: str):
    if not contact_person:
        return None, None
    parts = contact_person.split(maxsplit=1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else None
    return first, last


def validate_unique_client_fields(db: Session, client_id: uuid.UUID, update_data: dict):
    if "contact_person" in update_data:
        first_name, last_name = split_contact_person(update_data["contact_person"])
        exists = db.query(Client).filter(
            Client.contact_person == update_data["contact_person"],
            Client.id != client_id,
        ).first()
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Contact person already exists"
            )
        
    if "email" in update_data:
        exists = db.query(Client).filter(
            Client.email == update_data["email"],
            Client.id != client_id,
        ).first()
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Client email already exists"
            )

    if "phone_number" in update_data:
        exists = db.query(Client).filter(
            Client.phone_number == update_data["phone_number"],
            Client.id != client_id
        ).first()
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Phone number already exists"
            )

    if "name_of_organisation" in update_data:
        exists = db.query(Client).filter(
            Client.name_of_organisation == update_data["name_of_organisation"],
            Client.id != client_id
        ).first()
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Name of organisation already exists"
            )


def client_paginate_queryset(query, page, page_size, base_url, schema):
    total = query.count()
    offset = (page - 1) * page_size

    items = query.offset(offset).limit(page_size).all()

    results = [
        schema.model_validate(item, from_attributes=True)
        for item in items
    ]

    next_url = (
        f"{base_url}?page={page + 1}&page_size={page_size}"
        if offset + page_size < total
        else None
    )
    prev_url = (
        f"{base_url}?page={page - 1}&page_size={page_size}"
        if page > 1
        else None
    )

    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": results,
    }
