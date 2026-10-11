CREATE DATABASE IF NOT EXISTS portfolio
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE portfolio;

CREATE TABLE IF NOT EXISTS contact_messages (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(254) NOT NULL,
  phone VARCHAR(32) NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_contact_messages_created_at (created_at)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS portfolio (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  slug VARCHAR(120) NOT NULL,
  title VARCHAR(160) NOT NULL,
  category VARCHAR(120) NOT NULL,
  description TEXT NOT NULL,
  brief TEXT NOT NULL,
  focus TEXT NOT NULL,
  tools JSON NOT NULL,
  workflow JSON NOT NULL,
  is_published BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_portfolio_slug (slug),
  KEY idx_portfolio_published_order (is_published, sort_order, id)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS portfolio_media (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  project_id BIGINT UNSIGNED NOT NULL,
  media_type ENUM('image', 'video') NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(80) NOT NULL,
  alt_text VARCHAR(255) NOT NULL DEFAULT '',
  binary_data LONGBLOB NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_portfolio_media_project_order (project_id, sort_order, id),
  CONSTRAINT fk_portfolio_media_project
    FOREIGN KEY (project_id) REFERENCES portfolio (id)
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS portfolio_site_assets (
  asset_key VARCHAR(80) NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(80) NOT NULL,
  binary_data LONGBLOB NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (asset_key)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
