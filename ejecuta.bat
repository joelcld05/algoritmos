taskkill /F /IM python.exe
python "C:\cambiar\aqui\manage.py" runserver
timeout /t 5 /nobreak
start chrome http://localhost:8000/