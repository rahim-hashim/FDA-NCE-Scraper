import time
import requests

def test_connection(url, sleep_time=20):
	headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"}
	# use a while loop to keep trying to connect until it works, for a maximum of 5 times
	max_tries = 2
	for i in range(max_tries):
		try:
			response = requests.get(url, headers=headers)
		except requests.exceptions.ConnectionError:
			print(f'  Connection error: waiting {sleep_time}s before trying again (n={i}/{max_tries})...')
			time.sleep(20)
			response = requests.get(url, headers=headers)
		# also except ChunkedEncodingError
		except requests.exceptions.ChunkedEncodingError:
			print(f'  Chunked encoding error: waiting {sleep_time}s before trying again (n={i}/{max_tries})...')
			time.sleep(20)
			response = requests.get(url, headers=headers)
		if response.status_code == 200:
			return response
		if response.status_code == 404:
			# print(f'  Status code {response.status_code}: {url} does not exist...')
			break
			return response
		if response.status_code == 502:
			# print(f'  Status code {response.status_code}: waiting {sleep_time}s before trying again (n={i}/{max_tries})...')
			time.sleep(sleep_time)
		else:
			# print(f'  Status code {response.status_code} for {url}')
			time.sleep(sleep_time)
	return response