#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install Flask==3.0.0 requests==2.31.0 python-dotenv==1.0.1 gunicorn==21.2.0 ffmpeg-python==0.2.0 simpleaudio==1.0.4
pip install git+https://github.com/jiaaro/pydub.git@master
