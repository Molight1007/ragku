' Create Desktop Shortcut
Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

sScriptDir = oFSO.GetParentFolderName(WScript.ScriptFullName)
sExePath = sScriptDir & "\dist\RAG启动器\RAG启动器.exe"
sShortcutPath = oShell.SpecialFolders("Desktop") & "\RAG启动器.lnk"

If Not oFSO.FileExists(sExePath) Then
    MsgBox "EXE not found: " & sExePath, vbCritical, "Error"
    WScript.Quit
End If

Set oShortcut = oShell.CreateShortcut(sShortcutPath)
oShortcut.TargetPath = sExePath
oShortcut.WorkingDirectory = oFSO.GetParentFolderName(sExePath)
oShortcut.Description = "RAG Launcher"
oShortcut.Save

MsgBox "Shortcut created!" & vbCrLf & "Double-click RAG启动器 on Desktop", vbInformation, "Done"
