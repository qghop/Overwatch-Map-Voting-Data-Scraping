import subprocess
import os
import cv2
import numpy as np
from PIL import Image
import imagehash
import pandas as pd
from io import BytesIO
import easyocr
import gc

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

def preprocess_for_easyocr(img):
    scale_factor = 2.0
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Upscale the image
    height, width = gray.shape
    upscaled = cv2.resize(gray, (int(width * scale_factor), int(height * scale_factor)), interpolation=cv2.INTER_CUBIC)

    # slight sharpening
    kernel = np.array([[0, -1, 0],
                       [-1, 5,-1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(upscaled, -1, kernel)
    return sharpened


# OCR
def ocr_on_frame(pil_image, regions, reader, user_name, url, created_at, output_dir, debug=False):
    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    height, width = image.shape[:2]
    row_data = {
        'user_name': user_name,
        'vod_url': url,
        'created_at': created_at
    }
    for label, (ry1, ry2, rx1, rx2) in regions.items():
        y1 = int(ry1 * height)
        y2 = int(ry2 * height)
        x1 = int(rx1 * width)
        x2 = int(rx2 * width)
        cropped = image[y1:y2, x1:x2]
        processed = preprocess_for_easyocr(cropped)
        if debug:
            path = os.path.join(output_dir, f"{label}.png")
            cv2.imwrite(path, processed) # save image for debugging
        result = reader.readtext(processed, detail=0, paragraph=False)
        row_data[label] = result[0].strip() if result else '' # type: ignore
    
    return row_data


# Find all frames that have map vote data, and perform ocr
# Returns list of row data from vod info and OCR
def process_frames(m3u8_url, template_hashes, output_dir, user_name, url, created_at, regions, debug=False):
    reader = easyocr.Reader(['en'])
    
    skip_seconds_on_match = 60 * 13
    coarse_hash_threshold = 15 # TODO might need changing based on stream quality(?), overlays(?), looks good for now
    fine_hash_threshold = 10
    default_frame_interval = 13 # TODO might miss extremely fast votes
    fine_grained_frame_interval = .5 # TODO back to .5?
    frames_to_fine_grain_search = 35 / fine_grained_frame_interval # Map voting phase was at 20s, now 15 # TODO shorten for later
    
    current_time = 0
    in_fine_mode = False
    fine_grained_frames_remaining = frames_to_fine_grain_search
    coarse_match_time = 0  # Time to rewind to for fine-grained search
    found_rows = []

    # Looping through different pipes
    while True:
        effective_interval = fine_grained_frame_interval if in_fine_mode else default_frame_interval
        search_duration = frames_to_fine_grain_search * fine_grained_frame_interval if in_fine_mode else 0
        start_time = coarse_match_time if in_fine_mode else current_time

        if debug:
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

            # Looping through pipe
            while True:
                if not proc.stdout:
                    break

                # Read png
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
                frame_hash = imagehash.phash(crop_vote_area(frame))
                matched = False

                # Check frame against template hash
                for name, thash in template_hashes:
                    distance = thash - frame_hash
                    if in_fine_mode:
                        if distance <= fine_hash_threshold:
                            fine_matches.append((fine_grained_frames_remaining, distance, frame.copy()))
                            break
                    else:
                        if distance <= coarse_hash_threshold:
                            matched = True
                            break

                # Move time, handle matches
                if in_fine_mode:
                    fine_grained_frames_remaining -= 1
                    if fine_grained_frames_remaining <= 0:
                        if fine_matches:
                            best = sorted(fine_matches, key=lambda x: (x[1], x[0]))[0]  # (index, distance, frame)
                            if debug:
                                print(f"Best fine-grained match found: frame {best[0]} with distance {best[1]}")
                                match_path = os.path.join(output_dir, f"match_dist_{best[1]}.png")
                                best[2].save(match_path)
                            row = ocr_on_frame(best[2], regions, reader, user_name, url, created_at, output_dir, debug)
                            print(row.keys())
                            found_rows.append(row)
                            current_time = coarse_match_time + best[0] * fine_grained_frame_interval + skip_seconds_on_match
                            del best
                            del row
                            gc.collect
                        else:
                            if debug:
                                print("No fine-grained matches found within threshold.")
                            current_time = coarse_match_time + search_duration  # move past fine search window
                        in_fine_mode = False
                        proc.terminate()
                        if frame:
                            frame.close()
                            del frame
                        if frame_hash:
                            del frame_hash
                        break
                else:
                    current_time += effective_interval
                    if matched:
                        if debug:
                            print("Coarse match found. Entering fine-grained search.")
                        in_fine_mode = True
                        fine_grained_frames_remaining = frames_to_fine_grain_search
                        coarse_match_time = current_time - effective_interval  # rewind to start of matched frame
                        proc.terminate()
                        if frame:
                            frame.close()
                            del frame
                        if frame_hash:
                            del frame_hash
                        break

                # Free memory for each frame
                if frame:
                    frame.close()
                    del frame
                if frame_hash:
                    del frame_hash
                
                # Print every hour if debug is enabled
                current_time = round(current_time, 2)  # Round to avoid floating point issues
                if debug and current_time % 3600 < effective_interval:  # Print every hour
                    print(f"Current time: {current_time:.2f} seconds")
                    print(f"Processed frame at {current_time:.2f} seconds, found {len(found_rows)} rows so far.")

        except EOFError:
            if debug:
                print("Reached end of stream.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break
        finally:
            proc.terminate()
    
    return found_rows
