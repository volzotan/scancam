sudo cp mjpg-streamer.service /etc/systemd/system/

sudo apt-get update && sudo apt-get install -y git cmake libjpeg8-dev

cd ~

git clone https://github.com/jacksonliam/mjpg-streamer

cd mjpg-streamer/mjpg-streamer-experimental
make
sudo make install

sudo systemctl enable mjpg-streamer.service
sudo systemctl start mjpg-streamer.service