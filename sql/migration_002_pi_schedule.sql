-- Если база уже создана ранее, выполните этот файл один раз.
SET NAMES utf8mb4;

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
