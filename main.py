
from flask import Flask, request, jsonify, url_for, send_from_directory
import os
import json
import whisper
import moviepy.editor as mp
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.io.VideoFileClip import VideoFileClip
import os
import time
import textwrap

import shutil

app = Flask(__name__, static_url_path='', static_folder='results')

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
FONT_PATHS = {
    'Roboto': 'C:/Users/munee/PycharmProjects/newsub/fonts/Roboto/Roboto-Regular.ttf',
    'OpenSans': 'C:/Users/munee/PycharmProjects/newsub/fonts/Open_Sans/static/OpenSans-Regular.ttf',
    'Lato': 'C:/Users/munee/PycharmProjects/newsub/fonts/Lato/Lato-Regular.ttf',
    'Poppins': 'C:/Users/munee/PycharmProjects/newsub/fonts/Poppins/Poppins-Regular.ttf',
    'Merriweather': 'C:/Users/munee/PycharmProjects/newsub/fonts/Merriweather/Merriweather-Regular.ttf',
    'Montserrat': 'C:/Users/munee/PycharmProjects/newsub/fonts/Montserrat/static/Montserrat-Regular.ttf',
    'Oswald': 'C:/Users/munee/PycharmProjects/newsub/fonts/Oswald/static/Oswald-Regular.ttf',
    'Raleway': 'C:/Users/munee/PycharmProjects/newsub/fonts/Raleway/static/Raleway-Regular.ttf',
    'RobotoSlab': 'C:/Users/munee/PycharmProjects/newsub/fonts/Roboto_Slab/static/RobotoSlab-Regular.ttf',
    'Permanent Marker': 'C:/Users/munee/PycharmProjects/newsub/fonts/Permanent_Marker/PermanentMarker-Regular.ttf',
    'Lobster': 'C:/Users/munee/PycharmProjects/newsub/fonts/Lobster/Lobster-Regular.ttf',
    'Comfortaa': 'C:/Users/munee/PycharmProjects/newsub/fonts/Comfortaa/static/Comfortaa-Regular.ttf',
    'Pacifico': 'C:/Users/munee/PycharmProjects/newsub/fonts/Pacifico/Pacifico-Regular.ttf',
    'DancingScript': 'C:/Users/munee/PycharmProjects/newsub/fonts/Dancing_Script/static/DancingScript-Regular.ttf',
    'Bebas Neue': 'C:/Users/munee/PycharmProjects/newsub/fonts/Bebas_Neue/BebasNeue-Regular.ttf',
    'Bungee Spice': 'C:/Users/munee/PycharmProjects/newsub/fonts/Bungee_Spice/BungeeSpice-Regular.ttf'

}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

RESULTS_FOLDER = 'results'

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'webm', 'ts', 'avi', 'y4m', 'mkv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        task_type = request.form.get('task_type', 'transcribe')
        target_language = request.form.get('target_language', None)  # None if not provided
        print(target_language, task_type)

        try:
            subtitles = generate_subtitle_data(filename, task_type, target_language)
            return jsonify({
                'message': 'Subtitles generated successfully',
                'subtitles': subtitles
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid file type'}), 400


def generate_subtitle_data(video_filename, task_type='transcribe', target_language=None):
    video_path = os.path.join(UPLOAD_FOLDER, video_filename)
    audio_path = os.path.splitext(video_path)[0] + '.mp3'

    try:
        # Extract audio from the video
        clip = mp.VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, codec="mp3")

        # Load and use Whisper model for transcription
        model = whisper.load_model("base")
        target_language = request.form.get('target_language')
        if task_type == 'transcribe' and target_language:
            result = model.transcribe(audio_path, language=target_language)
        elif task_type == 'translate':
            result = model.transcribe(audio_path, task='translate')
        else:
            # Default to transcribe in English if no target language is provided
            result = model.transcribe(audio_path)
        subtitles = [{
            'start': segment['start'],
            'end': segment['end'],
            'text': segment['text']
        } for segment in result['segments']]

        os.remove(audio_path)  # Clean up the extracted audio file
        return subtitles
    except Exception as e:
        print(f"Error generating subtitles: {e}")
        raise


@app.route("/subtitles/<filename>", methods=['GET'])
def get_subtitles(filename):
    base_filename, _ = os.path.splitext(filename)
    subtitles_path = os.path.join(RESULTS_FOLDER, f'{base_filename}_subtitles.json')
    if os.path.exists(subtitles_path):
        with open(subtitles_path, 'r') as file:
            subtitles = json.load(file)
        return jsonify(subtitles)
    else:
        return jsonify({"error": "Subtitle file not found"}), 404


@app.route('/results/<path:filename>')
def custom_static(filename):
    return send_from_directory(RESULTS_FOLDER, filename)


@app.route("/process-subtitles", methods=['POST'])
def process_subtitles():
    content = request.json
    filename = content['filename']
    edited_subtitles = content['edited_subtitles']
    # Get the color preferences from the request
    bg_color = content.get('bg_color', '#000000')  # default black if not provided
    fg_color = content.get('fg_color', '#FFFFFF')  # default white if not provided
    font = content.get('font', 'Arial')  # default Arial if not provided

    video_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found'}), 404

    processed_video_path = generate_video_with_subtitles(
        video_path,
        edited_subtitles,
        bg_color,
        fg_color,
        font
    )
    if processed_video_path:
        video_url = url_for('static', filename=os.path.basename(processed_video_path), _external=True)
        return jsonify({'message': 'Video processed successfully', 'video_url': video_url})
    else:
        return jsonify({'error': 'Failed to process video'}), 500


def generate_video_with_subtitles(video_path, subtitles, bg_color, fg_color, font_name=None):
    try:
        video_clip = VideoFileClip(video_path)
        subtitle_clips = []
        video_width = video_clip.w
        video_height = video_clip.h

        for sub in subtitles:
            font_path = None
            font_size = min(int(video_height / 25), 60)  # Adjust as needed

            if font_name:
                # Format font name and retrieve font path if specified
                font_name_key = font_name.replace('_', ' ')
                print(font_name)

                font_path = FONT_PATHS.get(font_name_key, None)  # Return None if font is not found
                print(font_path)

            # Wrap the text and create a list of TextClips
            wrapped_lines = wrap_text(sub['text'], video_width, font_size)

            for i, line in enumerate(wrapped_lines):
                # Check if a valid font path exists
                if font_path:
                    txt_clip = TextClip(line, fontsize=font_size, font=font_path, color=fg_color, bg_color=bg_color,
                                        align='center')
                else:
                    # Skip font argument if no valid font path
                    txt_clip = TextClip(line, fontsize=font_size, color=fg_color, bg_color=bg_color, align='center')

                # Calculate vertical position for subtitle line
                line_position = ('center', video_height - (len(wrapped_lines) - i) * (txt_clip.size[1] + 5))

                # Set position, start, and duration for the subtitle clip
                txt_clip = txt_clip.set_position(line_position).set_start(sub['start']).set_duration(
                    sub['end'] - sub['start'])

                subtitle_clips.append(txt_clip)

        # Overlay the subtitle clips on the video clip
        final_clip = CompositeVideoClip([video_clip] + subtitle_clips)

        output_filename = 'processed_' + os.path.basename(video_path)
        output_path = os.path.join('results', output_filename)

        # Write the output video file with subtitles
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', bitrate='8000k')

        return output_path
    except Exception as e:
        print(f"Failed to process video: {str(e)}")
        return None


def wrap_text(text, video_width, font_size):
    # Assuming a default character width based on font size (could be adjusted for accuracy)
    char_width = font_size * 0.6  # An estimation; adjust as needed for better accuracy

    # Calculate the maximum number of characters per line
    max_chars_in_line = max(1, int(video_width / char_width))

    # Wrap the text based on the maximum number of characters per line
    wrapped_text = textwrap.fill(text, width=max_chars_in_line)
    return wrapped_text.split('\n')  # Split the wrapped text into lines


def secure_filename(filename):
    # Ensure the filename is secure
    return os.path.basename(filename)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
