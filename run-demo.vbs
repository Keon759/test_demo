Set shell = CreateObject("WScript.Shell")
scriptPath = Replace(WScript.ScriptFullName, "run-demo.vbs", "run-demo.bat")
shell.Run "cmd /k """ & scriptPath & """", 1, False
