taskkill /F /IM python.exe
python "./manage.py" runserver
timeout /t 5 /nobreak
start chrome http://localhost:8000/