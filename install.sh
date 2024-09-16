#!/bin/bash

#install python modules to root and user env
for file in modules/*.whl modules/*.tar.gz modules/*.zip; do
    pip3 install "$file"
done

pip install --no-index --find-links ./modules *.whl
pip install --no-index --find-links ./modules *.tar.gz
sudo pip install --no-index --find-links ./modules *.whl
sudo pip install --no-index --find-links ./modules *.tar.gz

#make default path to env
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

#delete recources lock files if any
sudo rm -f /home/pi/K96Rpi/locks/*

#stop and delete debian timesync service
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
sudo systemctl enable --now K96Rpi_sensor_info.timer
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
sudo systemctl enable --now K96Rpi_timesync.timer
echo -e "\033[1;32mK96Rpi timesync service installed and enabled.\033[0m"

#install data push service
echo -e "\033[1;33mInstalling K96Rpi data push service...\033[0m"
sudo systemctl stop K96Rpi_datapush.service
sudo systemctl disable K96Rpi_datapush.service
sudo rm -f /etc/systemd/system/K96Rpi_datapush.*
sudo cp -f datapush_service/K96Rpi_datapush.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now K96Rpi_datapush.service
echo -e "\033[1;32mK96Rpi datapush service installed and enabled.\033[0m"

#install file system management service
echo -e "\033[1;33mInstalling K96Rpi file system management service...\033[0m"
sudo systemctl stop K96Rpi_fsm.timer
sudo systemctl stop K96Rpi_fsm.service
sudo systemctl disable K96Rpi_fsm.timer
sudo systemctl disable K96Rpi_fsm.service
sudo rm -f /etc/systemd/system/K96Rpi_fsm.*
sudo cp -f fsm_service/K96Rpi_fsm.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now K96Rpi_fsm.timer
echo -e "\033[1;32mK96Rpi file system management service installed and enabled.\033[0m"

#install box monitoring service
echo -e "\033[1;33mInstalling K96Rpi hardware monitoring service...\033[0m"
sudo systemctl stop K96Rpi_hwmonitor.timer
sudo systemctl stop K96Rpi_hwmonitor.service
sudo systemctl disable K96Rpi_hwmonitor.timer
sudo systemctl disable K96Rpi_hwmonitor.service
sudo rm -f /etc/systemd/system/K96Rpi_hwmonitor.*
sudo cp -f hwmonitor_service/K96Rpi_hwmonitor.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now K96Rpi_hwmonitor.timer
echo -e "\033[1;32mK96Rpi hardware monitoring service installed and enabled.\033[0m"

#install data collection service
echo -e "\033[1;33mInstalling K96Rpi data collection service...\033[0m"
sudo systemctl stop K96Rpi_datacollection.service
sudo systemctl disable K96Rpi_datacollection.service
sudo rm -f /etc/systemd/system/K96Rpi_datacollection.*
sudo cp -f datacollection_service/K96Rpi_datacollection.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now K96Rpi_datacollection.service
echo -e "\033[1;32mK96Rpi data collection service installed and enabled.\033[0m"

#install data calculation service

#install automatic update service
echo -e "\033[1;33mInstalling K96Rpi software update service...\033[0m"
sudo systemctl stop K96Rpi_update.timer
sudo systemctl stop K96Rpi_update.service
sudo systemctl disable K96Rpi_update.timer
sudo systemctl disable K96Rpi_update.service
sudo rm -f /etc/systemd/system/K96Rpi_update.*
sudo cp -f softwareupdate_service/K96Rpi_update.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now K96Rpi_update.timer
echo -e "\033[1;32mK96Rpi K96Rpi software update service installed and enabled.\033[0m"

#install serial port listener service
echo -e "\033[1;33mInstalling K96Rpi calibration switch listener service...\033[0m"
sudo systemctl stop K96Rpi_seriallistener.service
sudo systemctl disable K96Rpi_seriallistener.service
sudo rm -f /etc/systemd/system/K96Rpi_seriallistener.*
sudo cp -f seriallistener_service/K96Rpi_seriallistener.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now K96Rpi_seriallistener.service
echo -e "\033[1;32mK96Rpi calibration switch listener service installed and enabled.\033[0m"

#restart the box
echo -e "\033[1;33mReloading systemd daemon...\033[0m"
sudo systemctl daemon-reload
echo -e "\033[1;33mRebooting the system...\033[0m"
sudo reboot
