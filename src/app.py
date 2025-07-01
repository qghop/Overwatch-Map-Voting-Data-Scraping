import os
import csv
from datetime import datetime, timezone
import argparse

import img_helper as img_helper
import twitch_helper as twitch_helper

template_fine_dir = 'templates_fine'
template_coarse_dir = 'templates_coarse'
output_dir = 'matches'

# regions for cropping before OCR
ref_w = 1920
ref_h = 1080
regions = { # y1, y2, x1, x2
    'map1_raw_text': (600 / ref_h, 640 / ref_h, 395 / ref_w, 685 / ref_w),
    'votes1_raw_text': (756 / ref_h, 787 / ref_h, 476 / ref_w, 578 / ref_w),
    'map2_raw_text': (600 / ref_h, 640 / ref_h, 810 / ref_w, 1100 / ref_w),
    'votes2_raw_text': (756 / ref_h, 787 / ref_h, 909 / ref_w, 1007 / ref_w),
    'map3_raw_text': (600 / ref_h, 640 / ref_h, 1225 / ref_w, 1545 / ref_w),
    'votes3_raw_text': (756 / ref_h, 787 / ref_h, 1339 / ref_w, 1448 / ref_w),
}

os.makedirs(output_dir, exist_ok=True)
template_hashes_fine = img_helper.load_template_hashes(template_fine_dir)
template_hashes_coarse = img_helper.load_template_hashes(template_coarse_dir)
vods_triples = ()

whitelist_raw_csv_path = 'vote_data_whitelisted.csv'
random_raw_csv_path = 'vote_data_random.csv'

def str2bool(v):
    return str(v).lower() in ("yes", "true", "t", "1")
parser = argparse.ArgumentParser(description="Map Vote Data Script Configuration")
parser.add_argument('--debug', type=str2bool, default=True, help="Enable debug mode")
parser.add_argument('--whitelist', type=str2bool, default=True, help="Run on whitelisted streamers")
parser.add_argument('--start-date', type=str, default="2025-06-30", help="Start date in YYYY-MM-DD")
parser.add_argument('--end-date', type=str, default="2027-01-01", help="End date in YYYY-MM-DD")
parser.add_argument('--vods-limit', type=int, default=100, help="Maximum number of VODs to process")
args = parser.parse_args()
start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
debug_mode = args.debug
run_whitelist = args.whitelist
vods_limit = args.vods_limit
print("Debug mode:", debug_mode)
print("Whitelist mode:", run_whitelist)
print("Start date:", start_date)
print("End date:", end_date)
print("VODs limit:", vods_limit)


# Get vods from whitelisted, currently all vods after patch day not already in csv
if run_whitelist:
    print("Updating Whitelist Data")
    # Load existing URLs from vote_data_whitelisted.csv
    existing_urls = set()
    if os.path.exists(whitelist_raw_csv_path):
        with open(whitelist_raw_csv_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    existing_urls.add(row[1])
    vods_triples = twitch_helper.get_whitelist_overwatch_vods('whitelist.csv', start_date, end_date)
    vods_triples = [v for v in vods_triples if v[1] not in existing_urls]

# Get vods from random streamers
else:
    print("Updating Random Data")
    full_vod_info = twitch_helper.get_random_overwatch_vods()
    vods_triples = [(v['user_name'], v['url'], v['created_at']) for v in full_vod_info]

vods_triples = vods_triples[:vods_limit]
print(f"{len(vods_triples)} Vods Found.")

for idx, (user_name, url, created_at) in enumerate(vods_triples):
    print(f"{idx + 1} / {len(vods_triples)}: {user_name}: {url}, {created_at} has begun.")
    # Get usable url
    m3u8_url = img_helper.get_m3u8_url(url)
    rows = []
    if not m3u8_url:
        print("Failed to get m3u8 url.")
        continue

    rows = img_helper.process_frames(m3u8_url, template_hashes_fine, template_hashes_coarse, 
                                     output_dir, user_name, url, created_at, regions, debug=debug_mode)
    if not rows:
        print("No frames found.")
        continue

    if run_whitelist:
        output_csv = whitelist_raw_csv_path
    else:
        output_csv = random_raw_csv_path

    with open(output_csv, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
        for row in rows:
            writer.writerow(row)
            
