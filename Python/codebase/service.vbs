' ============================================================================
' ACC Dashboard - Hidden Launcher (service.vbs)
' ============================================================================
' Runs start.bat without showing a console window.
' Used by Task Scheduler for background auto-start.
' ============================================================================

Set WshShell = CreateObject("WScript.Shell")

' Get the directory where this script lives
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Run start.bat hidden (0 = hidden, False = don't wait)
WshShell.Run """" & scriptDir & "\start.bat""", 0, False

Set WshShell = Nothing
