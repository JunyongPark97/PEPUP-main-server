from django.db.models import Q as q
from .serializers import FilterSerializer
from django.http.request import QueryDict

def set_filter(data):
    query = q()
    if data['category']:
        query = query & q(category=data['category'])
    if data['size']:
        query = query & q(size=data['size'])
    if data['brand']:
        query = query & q(brand__name=data['brand'])
    if data['on_sale']:
        query = query & q(on_sale=data['on_sale'])
    if data['min_price'] or data['max_price']:
        query = query & (q(price__gt=data['min_price']) | q(price__lt=data['max_price']))
    print(query)
    return query


def add_key_value(querydic, key, value):
    querydic[key] = value
    modifiedQuerydict = QueryDict('', mutable=True)
    modifiedQuerydict.update(querydic)
    return modifiedQuerydict