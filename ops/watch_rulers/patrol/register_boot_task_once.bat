@echo off
rem One-click registration of the boot task. Pure ASCII (cmd.exe reads .bat in the OEM codepage;
rem CJK here gets mis-decoded and some lines turn into commands -- verified 04:09).
rem
rem Why a separate .bat instead of putting it in stack_boot_restart.bat: registering a scheduled
rem task needs elevation, and the watch session must NOT raise a UAC prompt unattended. So the two
rem halves are split: stack_boot_restart.bat is what the task RUNS (no elevation), this file is
rem what a human runs ONCE to create the task (one UAC click).
rem
rem Idempotent: schtasks /Create /F overwrites an existing definition, so re-running is safe.
rem It does NOT start anything now; it only registers. To arm immediately, run
rem   D:\moodle\_qoder_cmdr_ref_20260921\live_checks\patrol\_watch_stack_r1.py
rem yourself.
set TASKNAME=CNXWatchStackBoot
set TR=D:\moodle\_qoder_cmdr_ref_20260921\live_checks\patrol\stack_boot_restart.bat
set LOG=%TEMP%\cnx_boottask_register.log
echo === %date% %time% register start ===> "%LOG%"
schtasks /Query /TN "%TASKNAME%" >nul 2>&1
if errorlevel 1 (
  echo NOT-FOUND: creating "%TASKNAME%"===>> "%LOG%"
) else (
  echo EXISTS: overwriting "%TASKNAME%"===>> "%LOG%"
)
schtasks /Create /F /TN "%TASKNAME%" /SC ONSTART /RU "%USERNAME%" /TR "%TR%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo REFUSE: schtasks failed, see "%LOG%"===>> "%LOG%"
  type "%LOG%"
  exit /b 1
)
echo --- verify ---===>> "%LOG%"
schtasks /Query /TN "%TASKNAME%" /FO LIST /V >> "%LOG%" 2>&1
type "%LOG%"
echo OK: "%TASKNAME%" registered; log at "%LOG%"
exit /b 0