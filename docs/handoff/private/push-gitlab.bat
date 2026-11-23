@echo off
rem Push the current Verity branch to the client GitLab as one new commit on top of phase_01.
rem The AI tooling folders (.agents, .claude, .cursor) are always left out of what is pushed.
rem Usage:  push-gitlab.bat "message"            (uses origin/feat/phase1-completion)
rem         push-gitlab.bat "message" origin/main (uses another branch)
setlocal
cd /d C:\Development\Verity_GRC_Platform
set GIT_AUTHOR_NAME=mehboob14
set GIT_AUTHOR_EMAIL=mehboobarshad300@gmail.com
set GIT_COMMITTER_NAME=mehboob14
set GIT_COMMITTER_EMAIL=mehboobarshad300@gmail.com
set MSG=%~1
if "%MSG%"=="" set MSG=Verity GRC platform: update
set SRC=%~2
if "%SRC%"=="" set SRC=origin/feat/phase1-completion

git fetch origin || goto :fail
git fetch gitlab || goto :fail

rem Build the tree in a throwaway index so your checkout is never touched.
set GIT_INDEX_FILE=%TEMP%\verity_gitlab_index
if exist "%GIT_INDEX_FILE%" del "%GIT_INDEX_FILE%"
git read-tree %SRC% || goto :fail
git rm -r -q --cached --ignore-unmatch .agents .claude .cursor || goto :fail
for /f %%i in ('git write-tree') do set TREE=%%i
set GIT_INDEX_FILE=
if "%TREE%"=="" goto :fail

for /f %%i in ('git commit-tree %TREE% -p gitlab/phase_01 -m "%MSG%"') do set COMMIT=%%i
if "%COMMIT%"=="" goto :fail
git push gitlab %COMMIT%:refs/heads/phase_01 || goto :fail
echo.
echo Pushed %COMMIT% to gitlab phase_01.
exit /b 0

:fail
echo.
echo Push failed. If GitLab says rejected, someone else committed to phase_01: tell Claude.
exit /b 1
