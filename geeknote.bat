echo off
rem %1 for first param, %* mean "all"
set args=%*    
echo args=%args% 
python build/lib/geeknote/geeknote.py %args%
