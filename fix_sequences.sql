-- Исправление sequence для таблиц (запустить в DBeaver если столы не грузятся)
-- Сбрасывает счётчики автоинкремента на правильные значения

SELECT setval(pg_get_serial_sequence('restaurant_order', 'id'),
    COALESCE((SELECT MAX(id) FROM restaurant_order), 0) + 1, false);

SELECT setval(pg_get_serial_sequence('restaurant_orderitem', 'id'),
    COALESCE((SELECT MAX(id) FROM restaurant_orderitem), 0) + 1, false);

SELECT setval(pg_get_serial_sequence('restaurant_table', 'id'),
    COALESCE((SELECT MAX(id) FROM restaurant_table), 0) + 1, false);

SELECT setval(pg_get_serial_sequence('restaurant_category', 'id'),
    COALESCE((SELECT MAX(id) FROM restaurant_category), 0) + 1, false);

SELECT setval(pg_get_serial_sequence('restaurant_dish', 'id'),
    COALESCE((SELECT MAX(id) FROM restaurant_dish), 0) + 1, false);

-- Проверка что столы есть и у них правильный статус
SELECT id, number, seats, status FROM restaurant_table ORDER BY number;
