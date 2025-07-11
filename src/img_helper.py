import subprocess
import os
import cv2
import numpy as np
from PIL import Image
import imagehash
import easyocr
import gc
import time

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
    left = int(0.3 * width)
    right = int(0.7 * width)
    top = int(0.14 * height)
    bottom = int(0.25 * height)
    return img.crop((left, top, right, bottom))

def load_template_hashes(folder):
    hashes = []
    for fname in os.listdir(folder):
        path = os.path.join(folder, fname)
        try:
            img = Image.open(path).convert('L')
            crop = crop_vote_area(img)
            #crop.save(f"test{fname}.png") # Save for debugging
            hashes.append((fname, imagehash.phash(crop)))
        except Exception as e:
            print(f"Failed to load template {fname}: {e}")
    return hashes

def preprocess_for_easyocr(img):
    scale_factor = 2.0
    
    # Convert to grayscale
    # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Upscale the image
    height, width = img.shape
    upscaled = cv2.resize(img, (int(width * scale_factor), int(height * scale_factor)), interpolation=cv2.INTER_CUBIC)

    # slight sharpening
    kernel = np.array([[0, -1, 0],
                       [-1, 5,-1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(upscaled, -1, kernel)
    return sharpened


# OCR
def ocr_on_frame(pil_image, regions, reader, user_name, url, created_at, output_dir, debug=False):
    #image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    image = np.array(pil_image)
    #height, width = image.shape[:2]
    height, width = image.shape
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

def get_vod_duration(m3u8_url):
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            m3u8_url
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"Error retrieving VOD duration: {e}")
        return float('inf')  # Fallback to very high limit

# Find all frames that have map vote data, and perform ocr
# Returns list of row data from vod info and OCR
def process_frames(m3u8_url, thashes_fine, thashes_coarse, output_dir, user_name, url, created_at, regions, debug=False):
    reader = easyocr.Reader(['en'])
    
    skip_seconds_on_match = 60 * 13
    coarse_hash_threshold = 15
    fine_hash_threshold = 10 
    default_frame_interval = 13
    fine_grained_frame_interval = .1 
    frames_to_fine_grain_search = 25 / fine_grained_frame_interval # Map voting phase was at 20s, now 15
    
    current_time = 0
    in_fine_mode = False
    fine_grained_frames_remaining = frames_to_fine_grain_search
    coarse_match_time = 0  # Time to rewind to for fine-grained search
    found_rows = []
    one_coarse_match_found = False
    vod_duration = get_vod_duration(m3u8_url)
    real_time_start = time.time()

    # Looping through different pipes
    while True:
        effective_interval = fine_grained_frame_interval if in_fine_mode else default_frame_interval
        search_duration = frames_to_fine_grain_search * fine_grained_frame_interval if in_fine_mode else 0
        start_time = coarse_match_time if in_fine_mode else current_time

        if debug:
            print(f"Starting FFmpeg at {start_time:.2f} seconds (interval = {effective_interval}s)...")

        # ffmpeg_cmd = [
        #     'ffmpeg',
        #     '-ss', str(start_time),
        #     '-i', m3u8_url,
        #     '-vf', f'fps=1/{effective_interval}',
        #     '-vcodec', 'png',
        #     '-f', 'image2pipe',
        #     '-loglevel', 'error',
        #     'pipe:1'
        # ]
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', m3u8_url,
            '-vf', f'fps=1/{effective_interval}, scale=1280:720',
            '-f', 'rawvideo',
            '-pix_fmt', 'gray', # 'rgb24' for RGB
            '-loglevel', 'error',
            'pipe:1'
        ]
        
        frame_width = 1280
        frame_height = 720
        frame_size = frame_width * frame_height # * 3 if RGB

        try:
            proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"FFmpeg failed: {e}")

        try:
            fine_matches = []

            # Looping through pipe
            while True:
                # small throttle
                time.sleep(0.01)
                
                if not proc.stdout:
                    break

                # # Read png
                # png_header = proc.stdout.read(8)
                # if not png_header:
                #     raise EOFError
                # if png_header != b'\x89PNG\r\n\x1a\n':
                #     continue
                # png_data = bytearray(png_header)
                # while True:
                #     chunk_len = int.from_bytes(proc.stdout.read(4), 'big')
                #     chunk_type = proc.stdout.read(4)
                #     chunk_data = proc.stdout.read(chunk_len)
                #     crc = proc.stdout.read(4)
                #     png_data += chunk_len.to_bytes(4, 'big') + chunk_type + chunk_data + crc
                #     if chunk_type == b'IEND':
                #         break

                # frame = Image.open(BytesIO(png_data)).convert('RGB')
                
                raw_frame = proc.stdout.read(frame_size)
                if not raw_frame:
                    raise EOFError
                frame_array = np.frombuffer(raw_frame, np.uint8).reshape((frame_height, frame_width)) # add , 3 after frame_width for RGB
                frame = Image.fromarray(frame_array, mode='L')  # 'L' for grayscale, delete for RGB
                
                frame_hash = imagehash.phash(crop_vote_area(frame))
                matched = False

                # # Check frame against template hash
                # for name, thash in template_hashes:
                #     distance = thash - frame_hash
                #     if in_fine_mode:
                #         if distance <= fine_hash_threshold:
                #             fine_matches.append((fine_grained_frames_remaining, distance, frame.copy()))
                #             break
                #     else:
                #         if distance <= coarse_hash_threshold:
                #             matched = True
                #             break
                
                # Check frame against template hashes depending on mode
                if in_fine_mode:
                    for name, thash in thashes_fine:
                        distance = thash - frame_hash
                        if distance <= fine_hash_threshold:
                            fine_matches.append((fine_grained_frames_remaining, distance, frame.copy()))
                            matched = True
                            break
                else:
                    for name, thash in thashes_coarse:
                        distance = thash - frame_hash
                        if distance <= coarse_hash_threshold:
                            matched = True
                            one_coarse_match_found = True
                            break

                # Move time, handle matches
                if in_fine_mode:
                    fine_grained_frames_remaining -= 1
                    if fine_grained_frames_remaining <= 0:
                        if fine_matches:
                            best = sorted(fine_matches, key=lambda x: (x[1], -x[0]))[0]  # (index, distance, frame)
                            if debug:
                                print(f"Best fine-grained match found: frame {best[0]} with distance {best[1]}")
                                match_path = os.path.join(output_dir, f"match.png")
                                best[2].save(match_path)
                            # TODO run OCR on all fine_matches? get best text, highest number of total votes?
                            row = ocr_on_frame(best[2], regions, reader, user_name, url, created_at, output_dir, debug)
                            for v in row.values(): print(v, end=' - ')
                            print()
                            found_rows.append(row)
                            current_time = coarse_match_time + best[0] * fine_grained_frame_interval + skip_seconds_on_match
                            del best
                            del row
                            gc.collect()
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
                if frame_hash: del frame_hash
                if frame_array.any(): del frame_array
                if raw_frame: del raw_frame
                
                # Break loop after 90 minutes if no coarse match found
                if not one_coarse_match_found and current_time >= 5400:
                    if debug:
                        print("Reached 90-minute no-match time limit. Exiting.")
                    raise EOFError
                
                # Break loop if after vod_duration (catch skipping past vod end)
                if current_time >= vod_duration:
                    if debug:
                        print("Reached or passed end of VOD. Exiting.")
                    raise EOFError

                # Break loop after 12 hours
                if current_time >= 43200:
                    if debug:
                        print("Reached 12hr time limit. Exiting.")
                    raise EOFError

                # Print every 5 minutes in hours:minutes format
                current_time = round(current_time, 2)
                if debug and current_time % 300 < effective_interval:
                    real_current_time = time.time()
                    real_elapsed_time = real_current_time - real_time_start
                    real_time_start = real_current_time
                    hours = int(current_time // 3600)
                    minutes = int((current_time % 3600) // 60)
                    print(f"Vod Progress: {hours:02d}:{minutes:02d}\t Step Took: {real_elapsed_time:.2f}s")

        except EOFError:
            if debug:
                print("Reached end of stream.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break
        finally:
            gc.collect()
            if proc.stdout:
                proc.stdout.close()
            proc.terminate()
            proc.wait()
    
    return found_rows
