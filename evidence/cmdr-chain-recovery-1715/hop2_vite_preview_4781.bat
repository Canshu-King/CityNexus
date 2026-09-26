@echo off
rem CMDR chain hop 2: vite preview :4781 serving the shared publish root
cd /d D:\moodle\_qoder_integration_20260919\frontend
set CITYNEXUS_BACKEND_PORT=8693
call npx vite preview --outDir D:/moodle/_qoder_preview_20260920/dist --host 127.0.0.1 --port 4781 --strictPort
