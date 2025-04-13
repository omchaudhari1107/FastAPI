import re
import random
import base64
from urllib.parse import quote
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = FastAPI(title="Terabox API", description="API to fetch file info and download links from Terabox URLs")

# Pydantic models for request and response validation
class TeraboxFileEntry(BaseModel):
    is_dir: str
    path: str
    fs_id: str
    name: str
    type: str
    size: str
    image: str
    list: List[Dict]

class TeraboxFileResponse(BaseModel):
    status: str
    sign: str
    timestamp: int
    shareid: int
    uk: int
    list: List[TeraboxFileEntry]

class TeraboxLinkResponse(BaseModel):
    status: str
    download_link: Dict[str, str]

class TeraboxURLRequest(BaseModel):
    url: HttpUrl

# Headers for requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.terabox.com/',
}

class TeraboxFile:
    def __init__(self):
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 104])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.headers = headers
        self.result = {'status': 'failed', 'sign': '', 'timestamp': '', 'shareid': '', 'uk': '', 'list': []}

    def search(self, url: str) -> None:
        try:
            req = self.session.get(url, headers=self.headers, allow_redirects=True, timeout=10)
            req.raise_for_status()
            self.short_url = re.search(r'surl=([^ &]+)', str(req.url)).group(1)
            self.get_sign()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

    def get_sign(self) -> None:
        api = 'https://terabox.hnn.workers.dev/api/get-info'
        post_url = f'{api}?shorturl={self.short_url}&pwd='
        headers_post = {
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Referer': 'https://terabox.hnn.workers.dev/',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
        }
        try:
            with requests.Session() as r:
                pos = r.get(post_url, headers=headers_post, allow_redirects=True, timeout=10).json()
                if pos.get('ok'):
                    self.result['sign'] = pos['sign']
                    self.result['timestamp'] = pos['timestamp']
                    self.result['shareid'] = pos['shareid']
                    self.result['uk'] = pos['uk']
                    self.result['list'] = self.pack_data(pos, self.short_url)
                    self.result['status'] = 'success'
                else:
                    raise HTTPException(status_code=400, detail="Failed to retrieve sign information")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"getSign error: {str(e)}")

    def pack_data(self, req: dict, short_url: str) -> List[Dict]:
        all_file = []
        for item in req.get('list', []):
            file_type = self.check_file_type(item['filename'])
            thumbnail = ''
            if file_type in ['image', 'video']:
                thumbs = item.get('thumbs', {})
                thumbnail = thumbs.get('url3') or thumbs.get('url2') or thumbs.get('url1') or ''

            file_entry = {
                'is_dir': '0' if not item.get('is_dir') else item['is_dir'],
                'path': item.get('filename', ''),
                'fs_id': item['fs_id'],
                'name': item['filename'],
                'type': file_type,
                'size': item.get('size', ''),
                'image': thumbnail,
                'list': [],
            }
            all_file.append(file_entry)
        return all_file

    def check_file_type(self, name: str) -> str:
        name = name.lower()
        if any(ext in name for ext in ['.mp4', '.mov', '.m4v', '.mkv', '.asf', '.avi', '.wmv', '.m2ts', '.3g2']):
            return 'video'
        return 'other'

class TeraboxLink:
    def __init__(self, shareid: str, uk: str, sign: str, timestamp: str, fs_id: str):
        self.domain = 'https://terabox.hnn.workers.dev/'
        self.api = f'{self.domain}api'
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 104])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.headers = {
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Referer': self.domain,
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
        }
        self.result = {'status': 'failed', 'download_link': {}}
        self.params = {
            'shareid': str(shareid),
            'uk': str(uk),
            'sign': str(sign),
            'timestamp': timestamp,
            'fs_id': fs_id,
        }
        self.base_urls = [
            'plain-grass-58b2.comprehensiveaquamarine',
            'royal-block-6609.ninnetta7875',
            'bold-hall-f23e.7rochelle',
            'winter-thunder-0360.belitawhite',
            'fragrant-term-0df9.elviraeducational',
            'purple-glitter-924b.miguelalocal'
        ]

    def generate(self) -> None:
        try:
            url_2 = f'{self.api}/get-downloadp'
            pos_2 = self.session.post(url_2, json=self.params, headers=self.headers, timeout=10).json()
            if 'downloadLink' in pos_2:
                self.result['download_link']['url_2'] = self.wrap_url(pos_2['downloadLink'])
                self.result['status'] = 'success'
            else:
                raise HTTPException(status_code=400, detail="No download link found in response")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"get-downloadp error: {str(e)}")
        finally:
            self.session.close()

    def wrap_url(self, original_url: str) -> str:
        selected_base = random.choice(self.base_urls)
        quoted_url = quote(original_url, safe='')
        b64_encoded = base64.urlsafe_b64encode(quoted_url.encode()).decode()
        return f'https://{selected_base}.workers.dev/?url={b64_encoded}'


@app.post("/file", response_model=TeraboxFileResponse)
async def get_file_info(request: TeraboxURLRequest):
    tf = TeraboxFile()
    tf.search(request.url)
    if tf.result['status'] == 'failed':
        raise HTTPException(status_code=400, detail="Failed to retrieve file information")
    
    return tf.result

@app.post("/link", response_model=TeraboxLinkResponse)
async def get_download_link(request: TeraboxURLRequest):
    # First, get file info
    tf = TeraboxFile()
    tf.search(request.url)
    if tf.result['status'] == 'failed' or not tf.result['list']:
        raise HTTPException(status_code=400, detail="Failed to retrieve file information or no files found")
    
    
    # Generate download link
    fs_id = tf.result['list'][0]['fs_id']
    uk = tf.result['uk']
    shareid = tf.result['shareid']
    timestamp = tf.result['timestamp']
    sign = tf.result['sign']
    
    tl = TeraboxLink(shareid, uk, sign, timestamp, fs_id)
    tl.generate()
    if tl.result['status'] == 'failed':
        raise HTTPException(status_code=400, detail="Failed to generate download link")
    
    return tl.result

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)