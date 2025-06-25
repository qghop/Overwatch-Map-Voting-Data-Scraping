import subprocess
import os
import cv2
import numpy as np
from PIL import Image
import imagehash
import pandas as pd

def get_m3u8_url(vod_url):
    try:
        result = subprocess.run(
            ['streamlink', vod_url, 'best', '--stream-url'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("Failed to get m3u8 URL from Twitch VOD.")
        print(e.stderr)
        return None
    
def crop_vote_area(img):
    width, height = img.size
    left = int(0.25 * width)
    right = int(0.75 * width)
    top = int(0.14 * height)
    bottom = int(0.25 * height)
    return img.crop((left, top, right, bottom))

def load_template_hashes(folder):
    hashes = []
    for fname in os.listdir(folder):
        path = os.path.join(folder, fname)
        try:
            img = Image.open(path).convert('RGB')
            crop = crop_vote_area(img)
            #crop.save(f"test{fname}.png") # Save for debugging
            hashes.append((fname, imagehash.phash(crop)))
        except Exception as e:
            print(f"Failed to load template {fname}: {e}")
    return hashes