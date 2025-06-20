from mutagen.oggvorbis import OggVorbis
from mutagen.flac import Picture
from pytubefix import YouTube
from moviepy import AudioFileClip
from pathlib import Path
from PIL import Image, ImageOps

import requests
import base64
import io
import os
import re

FSTR_OUTPUT_FOLDER_NAME = "{author} - {title} [{year}] [ogg]" # format will always be ogg
TEMP_AUDIO_FILE_NAME = "temp_audio.m4a"
COVER_CROPPED_PATH = "cover_cropped.jpg"
COVER_DEFAULT_SIZE = (720, 720)
DEFAULT_OGG_TITLE = "ogg_output"
COVER_THUMB_PATH = "cover_thumb.jpg"
FSTR_MAXRES_URL = "https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

def sanitize_filename(name: str) -> str:
  # regex blackmagic
  name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
  name = name.rstrip('. ')
  return name[:255]

def get_output_folder(youtube: YouTube) -> Path:
  output_folder_name = FSTR_OUTPUT_FOLDER_NAME.format(author=youtube.author, title=youtube.title, year=str(youtube.publish_date.year))
  folder_name = sanitize_filename(output_folder_name)

  output_folder = Path(folder_name)
  output_folder.mkdir(exist_ok=True)

  return output_folder

def convert_to_ogg(file_path: str, output_folder: Path, title=DEFAULT_OGG_TITLE) -> OggVorbis:
  output_path = output_folder / f"{sanitize_filename(title)}.ogg"

  if output_path.exists():
    output_path.unlink()

  audio = AudioFileClip(file_path)
  audio.write_audiofile(str(output_path), codec="libvorbis")
  audio.close()

  return OggVorbis(str(output_path))

def embed_cover(ogg_audio: OggVorbis, cover_image: Image):
  img_byte_arr = io.BytesIO()
  cover_image.save(img_byte_arr, format='JPEG') 
  img_byte_arr = img_byte_arr.getvalue()
  
  picture = Picture()
  picture.type = 3  
  picture.mime = "image/jpeg"
  picture.desc = "Cover"
  picture.data = img_byte_arr
  
  encoded_picture = picture.write()
  ogg_audio["metadata_block_picture"] = base64.b64encode(encoded_picture).decode('ascii')
  ogg_audio.save()

def write_metadata(ogg_audio: OggVorbis, youtube: YouTube, cover_image: Image = None):
  ogg_audio["TITLE"] = youtube.title 
  ogg_audio["ARTIST"] = youtube.author
  ogg_audio["DATE"] = str(youtube.publish_date.year)
  ogg_audio["TRACKNUMBER"] = "1"
  ogg_audio["DISCNUMBER"] = "1"
  ogg_audio["COMMENT"] = youtube.description
  ogg_audio["ALBUMARTIST"] = youtube.author
  ogg_audio["ALBUM"] = youtube.title
  
  if cover_image:
    embed_cover(ogg_audio, cover_image)
  else:
    ogg_audio.save()

def save_youtube_cover(youtube: YouTube, output_folder: Path, size=COVER_DEFAULT_SIZE) -> Image:
  request_url = FSTR_MAXRES_URL.format(video_id=youtube.video_id)

  response = requests.get(request_url)
  content = response.content

  thumb_path = output_folder / COVER_THUMB_PATH
  with open(thumb_path, "wb") as f:
    f.write(content)

  cropped = ImageOps.fit(Image.open(io.BytesIO(content)), size, centering=(0.5, 0.5))
  cropped_path = output_folder / COVER_CROPPED_PATH
  cropped.save(cropped_path)

  return cropped

def process_youtube_audio(url: str) -> OggVorbis:
  youtube = YouTube(url)
  
  output_folder = get_output_folder(youtube)

  temp_path = youtube.streams.get_audio_only().download(filename=TEMP_AUDIO_FILE_NAME)
  ogg_audio = convert_to_ogg(temp_path, output_folder, f"{youtube.author} - {youtube.title}")

  cover = save_youtube_cover(youtube, output_folder)
  
  write_metadata(ogg_audio, youtube, cover)
  os.remove(temp_path)
  print(f"All files saved to: {output_folder}")

  return ogg_audio

while True:
  process_youtube_audio(input("Enter YouTube URL: "))
  print("\n")