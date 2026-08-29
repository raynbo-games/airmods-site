import boto3, requests, os

bucket = "raynbo-games-site-storage"
cdn_url = "https://raynbo-games-site-storage.sfo3.cdn.digitaloceanspaces.com"

session = boto3.session.Session()
client = session.client(
    's3',
    region_name='sfo3',
    endpoint_url='https://raynbo-games-site-storage.sfo3.digitaloceanspaces.com',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
)

def get_image_cdn_url(directory, image_id):
    return f"{cdn_url}/{bucket}//images/{directory}/{image_id}.jpg"

def upload_to_spaces(directory, image_id, image_url):
    response = requests.get(image_url, stream=True)
    response.raise_for_status()
    
    file_path = f"/images/{directory}/{image_id}.jpg"
    client.put_object(
        Bucket=bucket,
        Key=file_path,
        Body=response.raw.read(),
        ACL='public-read',
        ContentType=response.headers.get('Content-Type', 'image/jpeg')
    )
    
    return get_image_cdn_url(directory, image_id)