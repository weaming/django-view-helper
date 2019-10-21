from typing import List, Tuple


def delete_keys(data: dict, keys: List[str]):
    if not data:
        return data
    assert isinstance(data, dict)
    for k in keys:
        if k in data:
            del data[k]
    return data


def extract_keys(data: dict, keys: List[str]):
    if not data:
        return {}
    assert isinstance(data, dict)
    rv = {k: data[k] for k in keys if k in data}
    delete_keys(data, keys)
    return rv


def rename_keys(data: dict, mp: List[Tuple[str, str]], search_fields: List[str] = None):
    for old, new in mp:
        if old in data:
            data[new] = data[old]
            del data[old]
    # apply renames, and then apply search_fields
    if search_fields:
        rename_keys(
            data, [(x, f"{x}__icontains") for x in search_fields if data.get(x)]
        )  # '' as exact query
    return data
