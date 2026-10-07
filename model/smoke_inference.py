"""Smoke the actual inference handler without requiring an HTTP client package."""
from io import BytesIO
import json
from pathlib import Path
from starlette.datastructures import UploadFile
import main_api

image = next((Path(__file__).parent/'惠山泥人图片标识').rglob('*.png'))
valid = main_api.predict_image(UploadFile(filename='sample.png', file=BytesIO(image.read_bytes())))
assert valid.status_code == 200 and json.loads(valid.body)['code'] == 0
invalid = main_api.predict_image(UploadFile(filename='bad.png', file=BytesIO(b'not an image')))
assert invalid.status_code == 400
oversize = main_api.predict_image(UploadFile(filename='large.png', file=BytesIO(b'x'*(main_api.MAX_IMAGE_BYTES+1))))
assert oversize.status_code == 413
print(json.dumps({'health':main_api.health(),'valid':valid.status_code,'invalid':invalid.status_code,'oversize':oversize.status_code},ensure_ascii=False))
