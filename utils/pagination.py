from utils.client_helpers import split_contact_person
from schemas.client import ClientOut

def paginate_queryset(query, page, page_size, base_url, schema):
    total = query.count()
    skip = (page - 1) * page_size
    records = query.offset(skip).limit(page_size).all()

    next_url = None
    prev_url = None

    if skip + page_size < total:
        next_url = f"{base_url}?page={page + 1}&page_size={page_size}"
    if page > 1:
        prev_url = f"{base_url}?page={page - 1}&page_size={page_size}"

    results = []
    for record in records:
        if schema is ClientOut:
            first, last = split_contact_person(record.contact_person)
            obj = schema.model_validate(record)
            obj.first_name = first
            obj.last_name = last
            results.append(obj)
        else:
            results.append(schema.model_validate(record))

    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": results
    }
