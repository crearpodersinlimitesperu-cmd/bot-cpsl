Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wscript.exe ""C:\Users\josem\Downloads\bot-cpsl-review\iniciar_crm_silente.vbs""", 0, False
WshShell.Run "wscript.exe ""C:\Users\josem\Downloads\bot-cpsl-review\lanzar_buscador_silente.vbs""", 0, False
WshShell.Run "wscript.exe ""C:\Users\josem\Downloads\bot-cpsl-review\lanzar_scheduler_silente.vbs""", 0, False
WshShell.Run "wscript.exe ""C:\Users\josem\Downloads\bot-cpsl-review\lanzar_agente_silente.vbs""", 0, False
WshShell.Run "wscript.exe ""C:\Users\josem\Downloads\bot-cpsl-review\lanzar_omnicanal_silente.vbs""", 0, False
Set WshShell = Nothing
