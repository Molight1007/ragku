' RAG本地知识库 - 完全隐藏控制台启动器
' 双击此文件启动 GUI 界面（无黑窗口）

Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

sScriptDir = oFSO.GetParentFolderName(WScript.ScriptFullName)

' 切换到脚本所在目录
oShell.CurrentDirectory = sScriptDir

' 检查虚拟环境
sVenvPath = sScriptDir & "\.venv\Scripts\python.exe"
If Not oFSO.FileExists(sVenvPath) Then
    ' 首次运行，需要创建虚拟环境（显示一个临时窗口）
    result = MsgBox("首次运行需要创建虚拟环境，可能需要几分钟。" & vbCrLf & "点击"是"继续", vbYesNo + vbQuestion, "RAG启动器")
    If result = vbNo Then
        WScript.Quit
    End If
    
    ' 显示临时窗口创建环境
    oShell.Run "cmd /c ""echo 正在创建虚拟环境... && python -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt -q && echo 完成 && timeout /t 2""", 1, True
End If

' 启动图形界面（完全隐藏控制台窗口）
' 0 = 隐藏窗口，False = 不等待程序结束
oShell.Run """" & sVenvPath & """ launcher.py""", 0, False

WScript.Quit
