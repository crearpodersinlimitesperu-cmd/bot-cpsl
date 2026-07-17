Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\josem\Downloads\bot-cpsl-review"
WshShell.Run "python ""C:\Users\josem\Downloads\bot-cpsl-review\task_scheduler_v2_1.py"" --daemon", 0, False

