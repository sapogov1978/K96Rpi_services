#!/bin/bash

#delete recources lock files if any
sudo rm -f /home/pi/K96Rpi/locks/*

#install sensor info service
echo -e "\033[1;33mStop K96Rpi sensor info service...\033[0m"
sudo systemctl stop K96Rpi_sensor_info.timer
sudo systemctl stop K96Rpi_sensor_info.service
echo -e "\033[1;32mK96Rpi sensor info service stopped.\033[0m"

#install time synchronization service
echo -e "\033[1;33mStop K96Rpi time sync service...\033[0m"
sudo systemctl stop K96Rpi_timesync.timer
sudo systemctl stop K96Rpi_timesync.service
echo -e "\033[1;32mK96Rpi timesync service stopped.\033[0m"

#install data push service
echo -e "\033[1;33mStop K96Rpi data push service...\033[0m"
sudo systemctl stop K96Rpi_datapush.service
echo -e "\033[1;32mK96Rpi datapush service stopped.\033[0m"

#install file system management service
echo -e "\033[1;33mStop K96Rpi file system management service...\033[0m"
sudo systemctl stop K96Rpi_fsm.timer
sudo systemctl stop K96Rpi_fsm.service
echo -e "\033[1;32mK96Rpi file system management service stopped.\033[0m"

#install box monitoring service
echo -e "\033[1;33mStop K96Rpi hardware monitoring service...\033[0m"
sudo systemctl stop K96Rpi_hwmonitor.timer
sudo systemctl stop K96Rpi_hwmonitor.service
echo -e "\033[1;32mK96Rpi hardware monitoring service stopped.\033[0m"

#install data collection service
echo -e "\033[1;33mStop K96Rpi data collection service...\033[0m"
sudo systemctl stop K96Rpi_datacollection.service
echo -e "\033[1;32mK96Rpi data collection service stopped.\033[0m"

#install data calculation service

#install automatic update service
echo -e "\033[1;33mStop K96Rpi software update service...\033[0m"
sudo systemctl stop K96Rpi_update.timer
sudo systemctl stop K96Rpi_update.service
echo -e "\033[1;32mK96Rpi K96Rpi software update service stopped.\033[0m"

#install serial port listener service
echo -e "\033[1;33mStop K96Rpi calibration switch listener service...\033[0m"
sudo systemctl stop K96Rpi_seriallistener.service
echo -e "\033[1;32mK96Rpi calibration switch listener service stopped.\033[0m"

#install usb manager service
echo -e "\033[1;33mStop K96Rpi usb connection manager service...\033[0m"
sudo systemctl stop K96Rpi_usb_manager.timer
sudo systemctl stop K96Rpi_usb_manager.service
echo -e "\033[1;32mK96Rpi usb connection manager service stopped.\033[0m"
