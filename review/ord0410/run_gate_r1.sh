#!/bin/bash
# ORD-0410 lane gate runner: own ports, own DB copy, no external AI key in the process env.
set -u
unset DEEPSEEK_API_KEY
unset CITYNEXUS_AI_API_KEY
export CITYNEXUS_E2E_PORT=4812
export CITYNEXUS_BACKEND_PORT=8712
export CITYNEXUS_PYTHON='D:/moodle/CityNexus/.venv/Scripts/python.exe'
export CITYNEXUS_DATABASE_URL='sqlite:///D:/moodle/_qoder_r_ord0410/run/_r_ord0410_e2e.db'
export CITYNEXUS_AI_ENABLED=false
export CITYNEXUS_EVIDENCE_DIR='D:/moodle/_qoder_r_ord0410/run/_gate_evidence'
cd /d/moodle/_qoder_r_ord0410/wt/frontend
exec npx --no-install playwright test "$@" --reporter=list
