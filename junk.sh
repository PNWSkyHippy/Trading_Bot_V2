cd /root/Trading_Bot_V2
chmod 600 .env
chmod +x Scripts/linux/*.sh

systemctl restart trading-bot.service
sleep 8

bash Scripts/linux/status.sh
journalctl -u trading-bot.service -n 80 --no-pager
