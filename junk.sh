cat > /opt/trading_bot_v2/.git/hooks/post-merge << 'EOF'
#!/bin/sh
chown -R ronh:ronh "$(git rev-parse --show-toplevel)"
EOF
chmod +x /opt/trading_bot_v2/.git/hooks/post-merge
