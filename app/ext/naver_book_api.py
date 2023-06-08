import requests
import os

headers = {
    'X-Naver-Client-Id': os.environ["NAVER_CLIENT_ID"],
    'X-Naver-Client-Secret': os.environ["NAVER_CLIENT_SECRET"],
}

def query_book(q):
  params = {
    'query': q,
    'display': '10',
    'start': '1',
  }

  response = requests.get('https://openapi.naver.com/v1/search/book.json', params=params, headers=headers)
  return response.text

def query_book_isbn(q):
  params = {
    'query': q,
    'display': '1',
    'start': '1',
  }

  response = requests.get('https://openapi.naver.com/v1/search/book.json', params=params, headers=headers)
  if "isbn" not in response.text:
    return False
  return response.text
