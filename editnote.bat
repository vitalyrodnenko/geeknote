echo off
rem %1 for first param, %* mean "all"
set title=%*    
echo title=%title% 

python build/lib/geeknote/geeknote.py edit --note %title% --content "WRITE"
