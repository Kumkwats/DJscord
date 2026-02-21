from dataclasses import dataclass
import requests


def get_content_type(url: str):
    return requests.head(url).headers["Content-Type"]
