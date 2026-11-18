@echo off
rem Adds "Pass to phone" to right-click > Send to (current user only) and removes the old "Phone (QR)". Delete the shortcut from shell:sendto to remove it.
rem Uses Pass.exe when it is built (run build.cmd), otherwise pythonw + pass_app.py.
powershell -NoProfile -Command "$here='%~dp0'.TrimEnd('\'); $exe=Join-Path $here 'Pass.exe'; $to=[Environment]::GetFolderPath('SendTo'); Remove-Item (Join-Path $to 'Phone (QR).lnk') -ErrorAction SilentlyContinue; $lnk=Join-Path $to 'Pass to phone.lnk'; $s=(New-Object -ComObject WScript.Shell).CreateShortcut($lnk); if (Test-Path $exe) { $s.TargetPath=$exe; $s.Arguments='' } else { $s.TargetPath=(Get-Command pythonw.exe).Source; $s.Arguments='\"'+(Join-Path $here 'pass_app.py')+'\"' }; $s.WorkingDirectory=$here; $s.IconLocation=(Join-Path $here 'icon.ico'); $s.Description='Send files to the phone over Wi-Fi with a QR code'; $s.Save(); Write-Output ('Added: '+$lnk)"
pause
