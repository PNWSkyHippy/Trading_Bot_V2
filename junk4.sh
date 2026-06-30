systemctl start web-dashboard.service
systemctl start breakout-scanner.service
systemctl start trading-bot.service

sleep 8
bash Scripts/linux/status.sh
journalctl -u trading-bot.service -n 80 --no-pager
