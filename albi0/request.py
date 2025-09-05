from httpx import AsyncClient

MAX_CONCURRENT = 10

header = {
	'user-agent': r'Mozilla/5.0 (Linux; Android 6.0.1; RIDGE 4G Build/LRX22G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2887.55 Mobile Safari/537.36',
	'referer': r'https://sp.61.com',
}

client = AsyncClient(headers=header)
