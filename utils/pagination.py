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



# def paginate_queryset(query, page, page_size, base_url, schema):
    # # If list, handle manually
    # if isinstance(query, list):
    #     total = len(query)
    #     start = (page - 1) * page_size
    #     end = start + page_size
    #     items = query[start:end]
    # else:
    #     total = query.count()
    #     items = query.offset((page - 1) * page_size).limit(page_size).all()

    # return {
    #     "data": [schema.model_validate(item) for item in items],
    #     "total": total,
    #     "page": page,
    #     "page_size": page_size,
    #     "total_pages": (total + page_size - 1) // page_size,
    #     "next": f"{base_url}?page={page+1}&page_size={page_size}" if (page * page_size) < total else None,
    #     "previous": f"{base_url}?page={page-1}&page_size={page_size}" if page > 1 else None
    # }
