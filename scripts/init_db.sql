-- Инициализация локальных баз данных для «Обещание против реальности».
-- Выполняется от суперпользователя postgres:
--   psql -U postgres -h localhost -f scripts/init_db.sql
--
-- Скрипт идемпотентен: существующие роль и базы не удаляются и не пересоздаются.

DO
$$
    BEGIN
        IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname = 'oapv_app') THEN
            CREATE ROLE oapv_app LOGIN PASSWORD 'oapv_local_dev';
        END IF;
    END
$$;

SELECT 'role oapv_app ready';

-- Рабочая база.
SELECT 'CREATE DATABASE obeshchanie OWNER oapv_app ENCODING ''UTF8'''
WHERE NOT EXISTS(SELECT FROM pg_database WHERE datname = 'obeshchanie')\gexec

-- Тестовая база (используется pytest, данные можно удалять без риска).
SELECT 'CREATE DATABASE obeshchanie_test OWNER oapv_app ENCODING ''UTF8'''
WHERE NOT EXISTS(SELECT FROM pg_database WHERE datname = 'obeshchanie_test')\gexec

SELECT 'databases obeshchanie / obeshchanie_test ready';
