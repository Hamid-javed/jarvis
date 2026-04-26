Dim python, jarvisDir
python = "C:\Python314\python.exe"
jarvisDir = "E:\projects\jarvis"
CreateObject("WScript.Shell").Run """" & python & """ """ & jarvisDir & "\wakeup.py""", 0, False
