@echo off
cd /d D:\moodle\_qoder_cmdr_ref_20260921\live_checks
python _cmdr_lan_static_api_r1.py --dist D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_day30/frontend/dist --port 4783 --api 4787 --log _lan_4783_log_day30.json
