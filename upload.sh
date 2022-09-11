HOSTNAME=pi

rsync -av * $HOSTNAME:/home/pi/slider --exclude "storage/*" --exclude "output/*" --exclude "input/*" --exclude "*.jpg"