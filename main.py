from __future__ import unicode_literals

import glob
import os
from os.path import join
from werkzeug.utils import secure_filename
from flask import Flask, request, send_file
import cv2
import whisper
import pandas as pd
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip

UPLOAD_FOLDER = 'inputs/vids'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'webm', 'ts', 'avi', 'y4m', 'mkv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def generate_subtitle_video(video_filename):
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
    audio_path = os.path.join('inputs', 'audio', 'audio.mp3')

    # Check if the audio file already exists, otherwise create it
    if not os.path.exists(audio_path):
        my_clip = mp.VideoFileClip(video_path)
        my_clip.audio.write_audiofile(audio_path, codec="libmp3lame")

    # Instantiate whisper model using model_type variable
    model = whisper.load_model('base')

    # Get text from speech for subtitles from audio file
    result = model.transcribe(audio_path, task='translate')

    # Create Subtitle dataframe
    dict1 = {'start': [], 'end': [], 'text': []}
    for i in result['segments']:
        dict1['start'].append(int(i['start']))
        dict1['end'].append(int(i['end']))
        dict1['text'].append(i['text'])
    df = pd.DataFrame.from_dict(dict1)

    # Get video properties
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    height = image.shape[0]
    width = image.shape[1]

    font_path = 'E:\\REM-VariableFont_wght.ttf'
    # Instantiate MoviePy subtitle generator with custom font, subtitles, and SubtitlesClip
    generator = lambda txt: mp.TextClip(
        txt,
        font=font_path,
        fontsize=width / 30,
        color='white',
        bg_color='black',  # Set background color to black
        size=(width, height * .28),
        method='caption'
    )

    subs = tuple(zip(tuple(zip(df['start'].values, df['end'].values)), df['text'].values))
    subtitles = SubtitlesClip(subs, generator)

    # Add subtitles to the video
    video = mp.VideoFileClip(video_path)
    final = mp.CompositeVideoClip([video, subtitles.set_pos(('center', 'bottom'))])

    # Release video resources
    vidcap = cv2.VideoCapture(video_path)
    release_video_resources(vidcap)

    # Save the video with subtitles
    video_with_subtitles_path = os.path.join('results', 'subbed_vids', 'video_with_subtitles.mp4')
    final.write_videofile(video_with_subtitles_path, fps=video.fps, remove_temp=True, codec="libx264",
                          audio_codec="aac")

    return video_with_subtitles_path
def remove_previous_files():
    # Release video resources and remove previous video files
    video_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*'))
    for video_file in video_files:
        try:
            vidcap = cv2.VideoCapture(video_file)  # Open video file
            release_video_resources(vidcap)        # Release video resources
        except Exception as e:
            print(f"Error releasing video resources: {str(e)}")
        try:
            os.remove(video_file)                  # Remove video file
        except Exception as e:
            print(f"Error removing video file: {str(e)}")

    # Remove previous subtitle files
    subtitle_files = glob.glob(os.path.join('results', 'subbed_vids', '*.mp4'))
    for subtitle_file in subtitle_files:
        try:
            os.remove(subtitle_file)
        except Exception as e:
            print(f"Error removing subtitle file: {str(e)}")

    # Remove previous audio file
    audio_file = os.path.join('inputs', 'audio', 'audio.mp3')
    if os.path.exists(audio_file):
        try:
            os.remove(audio_file)
        except Exception as e:
            print(f"Error removing audio file: {str(e)}")

def release_video_resources(vidcap):
    # Release video resources
    vidcap.release()

@app.route("/upload", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file and allowed_file(file.filename):
        try:
            remove_previous_files()

            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Generate subtitles
            video_with_subtitles_path = generate_subtitle_video(filename)

            # Ensure the video file resources are released
            with open(file_path, 'rb') as f:
                pass
            return send_file(video_with_subtitles_path, as_attachment=True)
        except Exception as e:
            return f"An error occurred: {str(e)}"
    return "Invalid file type"

if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0")
