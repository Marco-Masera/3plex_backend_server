
deploy:
	cp 3plex_backend_server.service /etc/systemd/system/3plex_backend_server.service 
	systemctl daemon-reload
	systemctl start 3plex_backend_server
	systemctl enable 3plex_backend_server

check_status:
	systemctl status 3plex_backend_server

view_logs:
	journalctl -u 3plex_backend_server

stop_service:
	systemctl stop 3plex_backend_server
	systemctl disable 3plex_backend_server