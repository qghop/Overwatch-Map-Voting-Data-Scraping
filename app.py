import subprocess
import os
import cv2
import numpy as np
from PIL import Image
import imagehash
from io import BytesIO
import pandas as pd
import easyocr

import img_helper
import twitch_helper

twitch_vod_url = 'https://www.twitch.tv/videos/2495517780' # appesax (random), 1 hr long, good quality, no overlap
#twitch_vod_url = 'https://www.twitch.tv/videos/2494835110' # zbra on patch day
template_dir = 'templates'
output_dir = 'matches' # for saving full images
skip_seconds_on_match = 60 * 8
coarse_hash_threshold = 10 # TODO might need changing based on stream quality(?), overlays(?)
fine_hash_threshold = 5
default_frame_interval = 10 # TODO might miss extremely fast votes
fine_grained_frame_interval = 0.5
frames_to_fine_grain_search = 23 / fine_grained_frame_interval

# regions for cropping before OCR
ref_w = 1920
ref_h = 1080
regions = {
    'map1_raw_text': (600 / ref_h, 640 / ref_h, 400 / ref_w, 685 / ref_w),
    'votes1_raw_text': (756 / ref_h, 787 / ref_h, 476 / ref_w, 578 / ref_w),
    'map2_raw_text': (600 / ref_h, 640 / ref_h, 810 / ref_w, 1100 / ref_w),
    'votes2_raw_text': (756 / ref_h, 787 / ref_h, 909 / ref_w, 1007 / ref_w),
    'map3_raw_text': (600 / ref_h, 640 / ref_h, 1230 / ref_w, 1540 / ref_w),
    'votes3_raw_text': (756 / ref_h, 787 / ref_h, 1339 / ref_w, 1448 / ref_w),
}

results_df = pd.DataFrame()
reader = easyocr.Reader(['en'])
os.makedirs(output_dir, exist_ok=True) # for saving full images
template_hashes = img_helper.load_template_hashes(template_dir)


# Find all frames that have map vote data
def process_frames(m3u8_url):
    frame_index = 0
    current_time = 0
    in_fine_mode = False
    fine_grained_frames_remaining = 0
    coarse_match_time = 0  # Time to rewind to for fine-grained search
    found_frames = []

    while True:
        effective_interval = fine_grained_frame_interval if in_fine_mode else default_frame_interval
        search_duration = frames_to_fine_grain_search * fine_grained_frame_interval if in_fine_mode else 0
        start_time = coarse_match_time if in_fine_mode else current_time

        print(f"Starting FFmpeg at {start_time:.2f} seconds (interval = {effective_interval}s)...")

        ffmpeg_cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', m3u8_url,
            '-vf', f'fps=1/{effective_interval}',
            '-vcodec', 'png',
            '-f', 'image2pipe',
            '-loglevel', 'error',
            'pipe:1'
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        try:
            fine_matches = []
            fine_index = 0

            while True:
                if not proc.stdout:
                    break

                png_header = proc.stdout.read(8)
                if not png_header:
                    raise EOFError
                if png_header != b'\x89PNG\r\n\x1a\n':
                    continue

                png_data = bytearray(png_header)
                while True:
                    chunk_len = int.from_bytes(proc.stdout.read(4), 'big')
                    chunk_type = proc.stdout.read(4)
                    chunk_data = proc.stdout.read(chunk_len)
                    crc = proc.stdout.read(4)

                    png_data += chunk_len.to_bytes(4, 'big') + chunk_type + chunk_data + crc
                    if chunk_type == b'IEND':
                        break

                frame = Image.open(BytesIO(png_data)).convert('RGB')
                frame_hash = imagehash.phash(img_helper.crop_vote_area(frame))

                matched = False

                for name, thash in template_hashes:
                    distance = thash - frame_hash

                    if in_fine_mode:
                        if distance <= fine_hash_threshold:
                            fine_matches.append((fine_index, distance, frame.copy()))
                            break
                    else:
                        if distance <= coarse_hash_threshold:
                            matched = True
                            break

                if in_fine_mode:
                    fine_index += 1
                    fine_grained_frames_remaining -= 1
                    if fine_grained_frames_remaining <= 0:
                        if fine_matches:
                            best = sorted(fine_matches, key=lambda x: (x[1], x[0]))[0]  # (index, distance, frame)
                            #print(f"Best fine-grained match found: frame {best[0]} with distance {best[1]}")
                            match_path = os.path.join(output_dir, f"match_{frame_index:04d}_{best[1]}.png")
                            best[2].save(match_path)
                            found_frames.append(best[2])
                            current_time = coarse_match_time + best[0] * fine_grained_frame_interval + skip_seconds_on_match
                        else:
                            #print("No fine-grained matches found within threshold.")
                            current_time = coarse_match_time + search_duration  # move past fine search window
                        in_fine_mode = False
                        proc.terminate()
                        break

                else:
                    frame_index += 1
                    current_time += effective_interval

                    if matched:
                        #print("Coarse match found. Entering fine-grained search.")
                        in_fine_mode = True
                        fine_grained_frames_remaining = frames_to_fine_grain_search
                        coarse_match_time = current_time - effective_interval  # rewind to start of matched frame
                        proc.terminate()
                        break

        except EOFError:
            #print("Reached end of stream.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break
        finally:
            proc.terminate()
        
    return found_frames


# Get usable url
m3u8_url = img_helper.get_m3u8_url(twitch_vod_url)
frames = []
if m3u8_url:
    print(f"M3U8 URL: {m3u8_url}")
    frames = process_frames(m3u8_url)
else:
    print("Failed to get m3u8 url.")


# Perform ocr
for pil_image in frames:

# Debug mode
# for fname in sorted(os.listdir(output_dir)):
#     if not fname.endswith('.png'):
#         continue
#     match_path = os.path.join(output_dir, fname)
#     pil_image = Image.open(match_path).convert('RGB')
    
    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    height, width = image.shape[:2]
    row_data = {}
    for label, (ry1, ry2, rx1, rx2) in regions.items():
        y1 = int(ry1 * height)
        y2 = int(ry2 * height)
        x1 = int(rx1 * width)
        x2 = int(rx2 * width)
        cropped = image[y1:y2, x1:x2]
        processed = img_helper.preprocess_for_easyocr(cropped)
        #cv2.imwrite(f'{label}.png', processed) # printing for debugging
        result = reader.readtext(processed, detail=0, paragraph=False)
        row_data[label] = result[0].strip() if result else '' # type: ignore

    results_df = pd.concat([results_df, pd.DataFrame([row_data])], ignore_index=True)


# Print results
print(results_df)


# Save to csv
#results_df.to_csv('simple_output.csv')