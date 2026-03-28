-- Отдельная база для Price Intelligence. Не пересекается с таблицами проекта «опрос».
-- CREATE DATABASE IF NOT EXISTS vtb_price_intel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE vtb_price_intel;

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS pi_platform (
  id           SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code         VARCHAR(32) NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  base_url     VARCHAR(512) NOT NULL,
  sort_order   SMALLINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pi_platform_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO pi_platform (code, display_name, base_url, sort_order) VALUES
  ('vtb',        'ВТБ Путешествия',     'https://vtb.aviakassa.ru/',       10),
  ('tbank',      'Т-Путешествия',       'https://www.tbank.ru/travel/',    20),
  ('alfa',       'Альфа Тревел',        'https://alfabank.ru/travel/',     30),
  ('aviasales',  'Aviasales',           'https://www.aviasales.ru/',       40),
  ('ostrovok',   'Островок',            'https://ostrovok.ru/',            50),
  ('yandex',     'Яндекс Путешествия',  'https://travel.yandex.ru/',       60),
  ('ozon',       'Ozon Travel',         'https://www.ozon.ru/travel',      70),
  ('tutu',       'tutu.ru',             'https://www.tutu.ru/',            80)
ON DUPLICATE KEY UPDATE display_name = VALUES(display_name), base_url = VALUES(base_url), sort_order = VALUES(sort_order);

CREATE TABLE IF NOT EXISTS pi_scenario (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  title               VARCHAR(512) NOT NULL,
  product_type        ENUM('avia','rail','hotel') NOT NULL DEFAULT 'avia',
  origin_label        VARCHAR(256) NOT NULL DEFAULT '',
  origin_code         VARCHAR(16)  NOT NULL DEFAULT '',
  destination_label   VARCHAR(256) NOT NULL DEFAULT '',
  destination_code    VARCHAR(16)  NOT NULL DEFAULT '',
  date_departure      DATE NOT NULL,
  date_return         DATE NULL,
  time_departure_pref VARCHAR(16) NULL COMMENT 'HH:MM или пусто',
  time_return_pref    VARCHAR(16) NULL,
  passengers_adults   TINYINT UNSIGNED NOT NULL DEFAULT 1,
  cabin_class         VARCHAR(32) NOT NULL DEFAULT 'economy',
  direct_only         TINYINT(1) NOT NULL DEFAULT 0,
  baggage_included    TINYINT(1) NOT NULL DEFAULT 0,
  tariff_notes        VARCHAR(512) NULL,
  status              ENUM('draft','pending','running','success','error') NOT NULL DEFAULT 'draft',
  last_error          TEXT NULL,
  created_at          DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at          DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY ix_pi_scenario_status (status),
  KEY ix_pi_scenario_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pi_run (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  scenario_id  BIGINT UNSIGNED NOT NULL,
  status       ENUM('running','success','error') NOT NULL DEFAULT 'running',
  started_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  finished_at  DATETIME(3) NULL,
  PRIMARY KEY (id),
  KEY ix_pi_run_scenario (scenario_id),
  CONSTRAINT fk_pi_run_scenario FOREIGN KEY (scenario_id) REFERENCES pi_scenario (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pi_result (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id        BIGINT UNSIGNED NOT NULL,
  platform_id   SMALLINT UNSIGNED NOT NULL,
  price_kopecks BIGINT UNSIGNED NULL,
  currency      CHAR(3) NOT NULL DEFAULT 'RUB',
  offer_url     VARCHAR(2048) NULL,
  error_text    TEXT NULL,
  raw_meta      JSON NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pi_result_run_platform (run_id, platform_id),
  KEY ix_pi_result_run (run_id),
  CONSTRAINT fk_pi_result_run FOREIGN KEY (run_id) REFERENCES pi_run (id) ON DELETE CASCADE,
  CONSTRAINT fk_pi_result_platform FOREIGN KEY (platform_id) REFERENCES pi_platform (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pi_schedule (
  id                      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  scenario_id             BIGINT UNSIGNED NOT NULL,
  interval_minutes        INT UNSIGNED NOT NULL DEFAULT 1440,
  enabled                 TINYINT(1) NOT NULL DEFAULT 1,
  last_scheduled_run_at   DATETIME(3) NULL,
  created_at              DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_pi_schedule_scenario (scenario_id),
  KEY ix_pi_schedule_enabled (enabled),
  CONSTRAINT fk_pi_schedule_scenario FOREIGN KEY (scenario_id) REFERENCES pi_scenario (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
