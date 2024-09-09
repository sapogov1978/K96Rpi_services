#!/bin/bash

LINE="export PYTHONPATH=$HOME/K96Rpi"
FILE="$HOME/.bashrc"
if grep -Fxq "$LINE" "$FILE"
then
    echo "Env variable aldady exist in $FILE"
else
    echo "$LINE" >> "$FILE"
    echo "PYTHONPATH path added to $FILE"
fi

source "$FILE"

sudo systemctl stop systemd-timesyncd.service 
sudo systemctl disable systemd-timesyncd.service
sudo systemctl daemon-reload

#install sensor info service
echo -e "\033[1;33mInstalling K96Rpi sensor info service...\033[0m"
sudo systemctl stop K96Rpi_sensor_info.timer
sudo systemctl stop K96Rpi_sensor_info.service
sudo systemctl disable K96Rpi_sensor_info.timer
sudo systemctl disable K96Rpi_sensor_info.service
sudo rm -f /etc/systemd/system/K96Rpi_sensor_info.*
sudo cp -f sensorinfo_service/K96Rpi_sensor_info.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable K96Rpi_sensor_info.timer
echo -e "\033[1;32mK96Rpi sensor info service installed and enabled.\033[0m"

#install time synchronization service
echo -e "\033[1;33mInstalling K96Rpi time sync service...\033[0m"
sudo systemctl stop K96Rpi_timesync.timer
sudo systemctl stop K96Rpi_timesync.service
sudo systemctl disable K96Rpi_timesync.timer
sudo systemctl disable K96Rpi_timesync.service
sudo rm -f /etc/systemd/system/K96Rpi_timesync.*
sudo cp -f timesync_service/K96Rpi_timesync.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable K96Rpi_timesync.timer
echo -e "\033[1;32mK96Rpi timesync service installed and enabled.\033[0m"

#install data push service

#install file system management service
echo -e "\033[1;33mInstalling K96Rpi file system management service...\033[0m"
sudo systemctl stop K96Rpi_fsm.timer
sudo systemctl stop K96Rpi_fsm.service
sudo systemctl disable K96Rpi_fsm.timer
sudo systemctl disable K96Rpi_fsm.service
sudo rm -f /etc/systemd/system/K96Rpi_fsm.*
sudo cp -f fsm_service/K96Rpi_fsm.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable K96Rpi_fsm.timer
echo -e "\033[1;32mK96Rpi file system management service installed and enabled.\033[0m"

#install data collection service

#install data calculation service

#install box monitoring service 

#restart the box
echo -e "\033[1;33mReloading systemd daemon...\033[0m"
sudo systemctl daemon-reload
echo -e "\033[1;33mRebooting the system...\033[0m"
sudo reboot
