from django.db.models import Q as q
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


def generate_s3_presigned_post(bucket, key, expiration, ext, acl='public-read'):
    content_type_map = {
        'jpg': 'image/jpeg',
        'mp3': 'audio/mpeg3',
        'mp4': 'video/mp4'
    }
    content_type = content_type_map[ext]
    # http://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.generate_presigned_post
    data = old_s3_client.generate_presigned_post(
        bucket,
        "%s.%s" % (key, ext),
        Fields={
            'acl': acl,
            'content-type': content_type,
            'bucket': bucket,
            'success_action_status': '201'
        },
        Conditions=[
            {'acl': acl},
            {'success_action_status': '201'},
            ['starts-with', '$content-type', content_type],
            ['content-length-range', 0, 100000000],  # (100MB)
        ],
        ExpiresIn=expiration, #60*24
    )
    data['host'] = data.pop('url')
    data['starts_with'] = []
    result = {
        'credentials': data,
        'image_key': key
    }
    return result