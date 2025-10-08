#!/usr/bin/env python3

import requests
import json

# Test the extract_text endpoint
url = "http://127.0.0.1:5000/extract_text"
data = {"url": "https://www.fondostech.in/"}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
