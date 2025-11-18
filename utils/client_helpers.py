def split_contact_person(contact_person: str):
    if not contact_person:
        return None, None
    parts = contact_person.split(maxsplit=1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else None
    return first, last