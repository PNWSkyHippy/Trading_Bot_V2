systemctl restart trading-bot.service web-dashboard.service
sleep 8
bash Scripts/linux/status.sh
journalctl -u trading-bot.service -n 80 --no-pager

