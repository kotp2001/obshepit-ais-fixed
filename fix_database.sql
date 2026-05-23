-- ============================================================
-- Скрипт починки БД obshepit_db для проекта АИС Общепит
-- Выполнить в DBeaver: открыть SQL Editor, вставить, запустить
-- ============================================================

-- 1. Добавить недостающее поле ready_at в restaurant_order
ALTER TABLE restaurant_order
    ADD COLUMN IF NOT EXISTS ready_at TIMESTAMP NULL;

-- 2. Создать системные таблицы Django (если не существуют)
CREATE TABLE IF NOT EXISTS django_migrations (
    id          BIGSERIAL PRIMARY KEY,
    app         VARCHAR(255) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    applied     TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS django_content_type (
    id        SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model     VARCHAR(100) NOT NULL,
    CONSTRAINT django_content_type_app_label_model_uniq UNIQUE (app_label, model)
);

CREATE TABLE IF NOT EXISTS auth_permission (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    content_type_id INT NOT NULL REFERENCES django_content_type(id),
    codename        VARCHAR(100) NOT NULL,
    CONSTRAINT auth_permission_content_type_id_codename_uniq UNIQUE (content_type_id, codename)
);

CREATE TABLE IF NOT EXISTS auth_group (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id            BIGSERIAL PRIMARY KEY,
    group_id      INT NOT NULL REFERENCES auth_group(id),
    permission_id INT NOT NULL REFERENCES auth_permission(id),
    CONSTRAINT auth_group_permissions_group_id_permission_id_uniq UNIQUE (group_id, permission_id)
);

CREATE TABLE IF NOT EXISTS auth_user (
    id           SERIAL PRIMARY KEY,
    password     VARCHAR(128) NOT NULL,
    last_login   TIMESTAMP WITH TIME ZONE NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username     VARCHAR(150) NOT NULL UNIQUE,
    first_name   VARCHAR(150) NOT NULL DEFAULT '',
    last_name    VARCHAR(150) NOT NULL DEFAULT '',
    email        VARCHAR(254) NOT NULL DEFAULT '',
    is_staff     BOOLEAN NOT NULL DEFAULT FALSE,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_user_groups (
    id       BIGSERIAL PRIMARY KEY,
    user_id  INT NOT NULL REFERENCES auth_user(id),
    group_id INT NOT NULL REFERENCES auth_group(id),
    CONSTRAINT auth_user_groups_user_id_group_id_uniq UNIQUE (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES auth_user(id),
    permission_id INT NOT NULL REFERENCES auth_permission(id),
    CONSTRAINT auth_user_user_permissions_user_id_permission_id_uniq UNIQUE (user_id, permission_id)
);

CREATE TABLE IF NOT EXISTS django_session (
    session_key  VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date  TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session(expire_date);

CREATE TABLE IF NOT EXISTS django_admin_log (
    id              SERIAL PRIMARY KEY,
    action_time     TIMESTAMP WITH TIME ZONE NOT NULL,
    object_id       TEXT NULL,
    object_repr     VARCHAR(200) NOT NULL,
    action_flag     SMALLINT NOT NULL CHECK (action_flag >= 0),
    change_message  TEXT NOT NULL,
    content_type_id INT NULL REFERENCES django_content_type(id),
    user_id         INT NOT NULL REFERENCES auth_user(id)
);

-- 3. Таблица профилей (роли сотрудников)
CREATE TABLE IF NOT EXISTS restaurant_profile (
    id       BIGSERIAL PRIMARY KEY,
    role     VARCHAR(20) NOT NULL DEFAULT 'waiter',
    pin_code VARCHAR(4) NULL,
    user_id  INT NOT NULL UNIQUE REFERENCES auth_user(id)
);

-- 4. Таблица журнала ТО (если вдруг нет)
CREATE TABLE IF NOT EXISTS restaurant_maintenancelog (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    work_performed  TEXT NOT NULL,
    performed_by    VARCHAR(100) NOT NULL,
    signature       VARCHAR(100) NOT NULL DEFAULT '',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 5. Добавить недостающие колонки в restaurant_order (если не добавились)
ALTER TABLE restaurant_order
    ADD COLUMN IF NOT EXISTS waiter_id INT NULL REFERENCES auth_user(id),
    ADD COLUMN IF NOT EXISTS guest_count INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS comment TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) NULL,
    ADD COLUMN IF NOT EXISTS total_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'new';

-- 6. Добавить недостающие колонки в restaurant_orderitem
ALTER TABLE restaurant_orderitem
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS comment VARCHAR(200) NOT NULL DEFAULT '';

-- 7. Помечаем миграции как применённые (чтобы Django не пытался создать таблицы заново)
INSERT INTO django_migrations (app, name, applied)
SELECT 'contenttypes', '0001_initial', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='contenttypes' AND name='0001_initial');

INSERT INTO django_migrations (app, name, applied)
SELECT 'contenttypes', '0002_remove_content_type_name', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='contenttypes' AND name='0002_remove_content_type_name');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0001_initial', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0001_initial');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0002_alter_permission_name_max_length', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0002_alter_permission_name_max_length');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0003_alter_user_email_max_length', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0003_alter_user_email_max_length');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0004_alter_user_username_opts', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0004_alter_user_username_opts');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0005_alter_user_last_login_null', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0005_alter_user_last_login_null');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0006_require_contenttypes_0002', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0006_require_contenttypes_0002');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0007_alter_validators_add_error_messages', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0007_alter_validators_add_error_messages');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0008_alter_user_username_validators', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0008_alter_user_username_validators');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0009_alter_user_last_name_max_length', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0009_alter_user_last_name_max_length');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0010_alter_group_name_max_length', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0010_alter_group_name_max_length');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0011_update_proxy_permissions', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0011_update_proxy_permissions');

INSERT INTO django_migrations (app, name, applied)
SELECT 'auth', '0012_alter_user_first_name_max_length', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='auth' AND name='0012_alter_user_first_name_max_length');

INSERT INTO django_migrations (app, name, applied)
SELECT 'admin', '0001_initial', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='admin' AND name='0001_initial');

INSERT INTO django_migrations (app, name, applied)
SELECT 'admin', '0002_logentry_remove_auto_add', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='admin' AND name='0002_logentry_remove_auto_add');

INSERT INTO django_migrations (app, name, applied)
SELECT 'admin', '0003_logentry_add_action_flag_choices', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='admin' AND name='0003_logentry_add_action_flag_choices');

INSERT INTO django_migrations (app, name, applied)
SELECT 'sessions', '0001_initial', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='sessions' AND name='0001_initial');

INSERT INTO django_migrations (app, name, applied)
SELECT 'restaurant', '0001_initial', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='restaurant' AND name='0001_initial');

-- 8. Проверочный запрос - должен вернуть все таблицы
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
