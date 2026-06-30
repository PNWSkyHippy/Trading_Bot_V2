chmod 600 /root/Trading_Bot_V2/.env
cd /root/Trading_Bot_V2
chmod +x Scripts/linux/*.sh
systemctl restart trading-bot.service
sleep 5
bash Scripts/linux/status.sh
journalctl -u trading-bot.service -n 80 --no-pager

