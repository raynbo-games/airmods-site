import boto3, requests, os

CDN_URL = "https://raynbo-games-site-storage.sfo3.cdn.digitaloceanspaces.com"

session = boto3.session.Session()
client = session.client(
    's3',
    region_name='sfo3',
    endpoint_url='https://raynbo-games-site-storage.sfo3.digitaloceanspaces.com',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
)

def get_image_cdn_url(directory, image_id):
    return f"{CDN_URL}/{directory}/images/{image_id}.jpg"

def upload_to_spaces(directory, image_id, image_url):
    response = requests.get(image_url, stream=True)
    response.raise_for_status()
    
    client.put_object(
        Bucket=directory,
        Key=f"images/{image_id}.jpg",
        Body=response.raw.read(),
        ACL='public-read',
        ContentType=response.headers.get('Content-Type', 'image/jpeg')
    )
    
    return get_image_cdn_url(directory, image_id)

def cdn(directory, name, extension):
    return f"{CDN_URL}/static/{directory}/{name}.{extension}"

def cdn_script(name):
    return cdn("script", name, "js")

def cdn_style(name):
    return cdn("style", name, "css")

def cdn_image(name):
    return cdn("image", name, "jpg")