@echo off
rem Boot/logon re-arming for the watch stack. Pure ASCII on purpose: cmd.exe reads .bat in the OEM
rem codepage, so CJK comments here get mis-decoded and some lines turn into commands (verified 03:5x).
rem
rem Why this exists: the 22:46 repair-install reboot took down BB hub (:4799), the human board
rem (:4820), the sentinel and the inbox applier. The stack is process-level, so nothing re-started
rem it until the next watch round -- that gap was 2h40m.
rem
rem Safety: _watch_stack_r1.py is idempotent. It enumerates by CIM CommandLine, starts only what is
rem missing, and never starts a second copy of a leg that is already alive. STOP times come from env,
rem so after a shift's stop time this script will not resurrect services.
rem
rem Registration is NOT done by the watch session. If the owner approves, run exactly:
rem   schtasks /Create /F /TN CNXWatchStackBoot /SC ONSTART /RU "%USERNAME%" /TR "D:\moodle\_qoder_cmdr_ref_20260921\live_checks\patrol\stack_boot_restart.bat"
rem Removal:
rem   schtasks /Delete /F /TN CNXWatchStackBoot
set HTTP_PROXY=
set HTTPS_PROXY=
set NO_PROXY=*
set PYEXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe
set STACKDIR=D:\moodle\_qoder_cmdr_ref_20260921\live_checks\patrol
cd /d "%STACKDIR%"
rem Stop times MUST be derived at boot, never inherited: the legs' compiled defaults are last
rem shift's literal dates (APPLIER_STOP=1005-1100, STACK_KEEPER_STOP=1004-1100), which on 10-06
rem are already in the past -- a leg started without them retires on its first tick while the
rem stack line still prints "stack complete". _stack_boot_env.py returns the next FUTURE instant
rem for each leg as KEY=VALUE lines (verified: boot at 23:50 rolls the date forward).
for /f "tokens=1,2 delims==" %%K in ('"%PYEXE%" _stack_boot_env.py 2^>nul') do set %%K=%%L
rem %date% prints a CJK weekday, which lands in the log as mojibake under the OEM codepage;
rem %time% alone is ASCII and sortable, and the stack line below carries its own date.
echo RUN %time% >> "%STACKDIR%\_stack_boot_restart.log"
echo STOP SUP=%SUP_STOP% SENT=%SENTINEL_STOP% AP=%APPLIER_STOP% KEE=%STACK_KEEPER_STOP% >> "%STACKDIR%\_stack_boot_restart.log"
if not exist "%PYEXE%" (
  echo REFUSE: python not at %PYEXE% >> "%STACKDIR%\_stack_boot_restart.log"
  exit /b 1
)
"%PYEXE%" _watch_stack_r1.py >> "%STACKDIR%\_stack_boot_restart.log" 2>&1
