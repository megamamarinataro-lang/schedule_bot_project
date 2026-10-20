import os
import gspread
import datetime
import time

# Глобальный словарь для реализации кэша в памяти
# Структура: {"data": все_записи_из_таблицы, "last_updated": время_в_секундах}
_schedule_cache = {
    "data": None,
    "last_updated": 0
}

# Время жизни кэша (TTL) — 300 секунд (5 минут)
CACHE_TTL = 300

def log_cache_status(message: str):
    """Служебное логирование времени обновления кэша и его статуса."""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] LOG КЭША: {message}")

def get_all_records_with_cache() -> list:
    """
    Получение всех записей из таблицы с использованием кэширования в памяти.
    Если кэш свежий (< 5 минут), данные берутся из памяти без запроса в интернет.
    """
    global _schedule_cache
    current_time = time.time()
    
    # Проверяем, есть ли данные в кэше и не истекло ли время жизни (TTL)
    if _schedule_cache["data"] is not None and (current_time - _schedule_cache["last_updated"]) < CACHE_TTL:
        log_cache_status("Данные взяты из быстрого кэша в памяти (запрос к API пропущен).")
        return _schedule_cache["data"]
    
    # Если кэш пустой или устарел — делаем реальный запрос к облаку Google
    log_cache_status("Кэш пуст или устарел. Выполняю реальный сетевой запрос к Google Sheets API...")
    
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open("Schedule_2026")
    
    # Используем sheet1 для открытия первого листа
    worksheet = sh.sheet1
    
    # Получить все записи через worksheet.get_all_records()
    records = worksheet.get_all_records()
    
    # Обновляем глобальный кэш новыми данными и фиксируем время обновления по ТЗ
    _schedule_cache["data"] = records
    _schedule_cache["last_updated"] = current_time
    log_cache_status("Глобальный кэш успешно обновлен свежими данными из облака.")
    
    return records

def get_schedule(group_name: str, day: str) -> str:
    """Реализация функции get_schedule ."""
    try:
        # Извлекаем записи (либо из интернета, либо из быстрого кэша)
        records = get_all_records_with_cache()
        
        today_lessons = []
        group_found = False
        
        # Перебираем строки таблицы по именам полей (без жесткого привязывания к индексам столбцов)
        for row in records:
            #  Фильтруем строки, где поле Группа соответствует запрошенной
            # Метод .get("Группа") ищет столбец по его имени!
            if str(row.get("Группа")).strip().lower() == group_name.strip().lower():
                group_found = True
                
                #  Фильтруем строки по полю День (или День недели)
                if str(row.get("День недели")).strip().lower() == day.strip().lower():
                    time_slot = row.get("Время")
                    subject = row.get("Название предмета")
                    room = row.get("Аудитория")
                    teacher = row.get("Преподаватель")
                    
                    today_lessons.append(f"⏰ {time_slot} — {subject} (Ауд. {room}, преп. {teacher})")
        
        # Если группа вообще не найдена в расписании
        if not group_found:
            return "Группа с таким номером нет."
            
        #  Если группа есть, но занятий на этот день нет
        if not today_lessons:
            return "В этот день не запланировано."
            
        # Формируем  текстовое сообщение104
        lessons_text = "\n".join(today_lessons)
        return f"📅 Расписание группы {group_name.upper()} на день ({day.upper()}):\n{lessons_text}"
        
    except gspread.exceptions.SpreadsheetNotFound:
        return "Ошибка: Google Таблица с именем 'Schedule_2026' не найдена. Проверьте её название и доступ робота."
    except Exception as e:
        return f"Произошла непредвиденная ошибка при обработке данных: {e}"

def main():
    print("=== Тестирование получения расписания (Google Sheets API) ===")
    
    # 1. Сначала спрашиваем ТОЛЬКО номер группы
    group = input("Введите номер группы (например, 104): ").strip()
    
    if group:
        print("\n⏳ Подключаюсь к Google Sheets для проверки группы...")
        try:
            # Получаем все записи (сработает наша система кэширования!)
            records = get_all_records_with_cache()
            
            # Быстро проверяем глазами, есть ли вообще такая группа в таблице
            group_exists = any(str(row.get("Группа")).strip().lower() == group.lower() for row in records)
            
            # 5. ТЗ: Если группа не найдена — МГНОВЕННО выводим ошибку и завершаем программу
            if not group_exists:
                print("\nОтвет бота:")
                print("Группа с таким номером не обнаружена в расписании.")
                return # Выходим из функции, завершая работу программы
                
        except Exception as e:
            print(f"\nОшибка при подключении к API: {e}")
            return
            
        # 2. Если группа существует, ТОЛЬКО ТОГДА спрашиваем день недели!
        day = input("Введите день недели (например, вт): ").strip()
        
        if day:
            # Вызываем уже готовую фильтрацию по дню
            result = get_schedule(group, day)
            print("\nОтвет бота:")
            print(result)


if __name__ == "__main__":
    main()
