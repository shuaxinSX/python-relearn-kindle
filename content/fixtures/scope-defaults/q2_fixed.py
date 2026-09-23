def add_tag(tag, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(tag)
    return bucket


print(add_tag("sql"))
print(add_tag("api"))
