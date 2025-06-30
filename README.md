# Overwatch Map Voting Data Scraping

Using machine vision and public twitch vods to get info on map popularity.

[Viewable on https://ow-map-voting-data.streamlit.app/](https://ow-map-voting-data.streamlit.app/)

Uses OpenCV, Pillow, ImageHash, and EasyOCR for Image Processing, Pandas for handling Data,  
Streamlink and FFmpeg CLI, as well as the Twitch API, for Stream Processing, Rapidfuzz for OCR Cleaning,  
and Streamlit and Plotly for front-end and data visualization.

## Screenshots

![Tier List](<screenshots/tier list.png>)

![Bar Chart](<screenshots/bar chart.png>)

## Requirements

Python 3.12, FFmpeg and Streamlink (see requirements.txt)

Run app.py to update raw data, and clean.py to clean the raw data. streamlit_app.py can be run locally with: streamlit run streamlit_app.py
