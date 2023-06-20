import requests
import os

headers = {
    'X-Naver-Client-Id': os.environ["NAVER_CLIENT_ID"],
    'X-Naver-Client-Secret': os.environ["NAVER_CLIENT_SECRET"],
}

def query_book(q):
  params = {
    'query': q,
    'display': '30',
    'start': '1',
  }

  res = requests.get('https://openapi.naver.com/v1/search/book.json', params=params, headers=headers)
  return res.text

def query_book_list():
  params = {
    'query': '프로그래밍',
    'display': '30',
    'start': '1',
  }

  res = requests.get('https://openapi.naver.com/v1/search/book.json', params=params, headers=headers)
  return res.json()

def query_book_isbn(q):
  params = {
    'query': q,
    'display': '1',
    'start': '1',
  }

  res = requests.get('https://openapi.naver.com/v1/search/book.json', params=params, headers=headers)
  if "isbn" not in res.text:
    return False
  return res.text
