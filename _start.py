import subprocess
import sys

abonements = '_abonements.py'
freezes = '_freezes.py'
services = '_services.py'
arr = {'1': abonements,
       '2': freezes,
       '3': services}

def run(path):
    try:
        subprocess.Popen(f'start cmd /k python "{path}"', shell=True)
    except Exception as e:
        print(f"Ошибка запуска: {e}")

path = input('1 - Абонементы\n2 - Заморозки\n3 - Услуги\n\nВведите нужную цифру: ')

run(arr[path])