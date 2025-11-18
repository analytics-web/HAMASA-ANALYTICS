from fastapi import Request

def paginate_queryset(query, page: int, page_size: int, base_url: str, schema):
    total = query.count()

    skip = (page - 1) * page_size
    records = query.offset(skip).limit(page_size).all()

    next_url = None
    prev_url = None

    if skip + page_size < total:
        next_url = f"{base_url}?page={page + 1}&page_size={page_size}"

    if page > 1:
        prev_url = f"{base_url}?page={page - 1}&page_size={page_size}"

    # convert ORM objects to Pydantic
    results = [schema.model_validate(r) for r in records]

    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": results
    }
