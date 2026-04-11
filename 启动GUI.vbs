' RAG本地知识库 - 图形界面启动器
' 双击此文件启动 GUI 界面

Set oShell = CreateObject("WScript.Shell")
sScriptDir = oShell.CurrentDirectory

' 切换到脚本所在目录
oShell.CurrentDirectory = sScriptDir

' 启动批处理文件
Set oExec = oShell.Exec("cmd /c ""启动GUI.bat""")

' 等待程序启动
WScript.Sleep 500

If oExec.Status = 0 Then
    ' 程序正在运行
    WScript.Quit
Else
    ' 程序启动失败，显示错误
    MsgBox "启动失败，请检查是否安装了 Python", vbCritical, "错误"
End If
