-- CaseHub schema snapshot.
-- Source of truth is the Alembic migrations in db/migrations/versions/ —
-- this file is a readable reference of the current schema, regenerated
-- from the live database as tables stabilize (not hand-edited).
--
-- Users was split into Identities (global login) + Memberships (role at one
-- tenant) — one identity can hold a membership at more than one firm.
-- Case access (both lawyers and clients) is many-to-many via
-- CaseAssignments, rather than single client_id/lawyer_id columns on Cases —
-- an office manager sees every case at their own tenant automatically
-- without needing a row here; super_admin never gets case-level access.

CREATE TABLE `tenants` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `subdomain` varchar(63) NOT NULL,
  `plan` enum('FREE','PRO','ENTERPRISE') NOT NULL,
  `logo_url` varchar(500) DEFAULT NULL,
  `primary_color` varchar(7) DEFAULT NULL,
  `active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_tenants_subdomain` (`subdomain`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `identities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `bio` text,
  `photo_url` varchar(500) DEFAULT NULL,
  `is_super_admin` tinyint(1) NOT NULL,
  `token_version` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_identities_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `memberships` (
  `id` int NOT NULL AUTO_INCREMENT,
  `identity_id` int NOT NULL,
  `tenant_id` int NOT NULL,
  `role` enum('SUPER_ADMIN','OFFICE_MANAGER','LAWYER','CLIENT') NOT NULL,
  `show_on_public_page` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_memberships_identity_tenant` (`identity_id`,`tenant_id`),
  KEY `ix_memberships_identity_id` (`identity_id`),
  KEY `ix_memberships_tenant_id` (`tenant_id`),
  CONSTRAINT `memberships_ibfk_1` FOREIGN KEY (`identity_id`) REFERENCES `identities` (`id`),
  CONSTRAINT `memberships_ibfk_2` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `cases` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `title` varchar(255) NOT NULL,
  `status` enum('OPEN','IN_PROGRESS','ON_HOLD','CLOSED') NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_cases_status` (`status`),
  KEY `ix_cases_tenant_id` (`tenant_id`),
  CONSTRAINT `cases_ibfk_1` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `case_assignments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `case_id` int NOT NULL,
  `membership_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_case_assignments_case_membership` (`case_id`,`membership_id`),
  KEY `ix_case_assignments_case_id` (`case_id`),
  KEY `ix_case_assignments_membership_id` (`membership_id`),
  KEY `ix_case_assignments_tenant_id` (`tenant_id`),
  CONSTRAINT `case_assignments_ibfk_1` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`),
  CONSTRAINT `case_assignments_ibfk_2` FOREIGN KEY (`membership_id`) REFERENCES `memberships` (`id`),
  CONSTRAINT `case_assignments_ibfk_3` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `case_id` int NOT NULL,
  `uploaded_by` int NOT NULL,
  `file_url` varchar(500) NOT NULL,
  `folder_type` enum('CLIENT','INTERNAL') NOT NULL,
  `visible_to` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `uploaded_by` (`uploaded_by`),
  KEY `ix_documents_case_id` (`case_id`),
  KEY `ix_documents_tenant_id` (`tenant_id`),
  CONSTRAINT `documents_ibfk_1` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`),
  CONSTRAINT `documents_ibfk_2` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`),
  CONSTRAINT `documents_ibfk_3` FOREIGN KEY (`uploaded_by`) REFERENCES `memberships` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `subscriptions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `plan` enum('FREE','PRO','ENTERPRISE') NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_subscriptions_tenant_id` (`tenant_id`),
  CONSTRAINT `subscriptions_ibfk_1` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `key` varchar(100) NOT NULL,
  `value` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_settings_tenant_key` (`tenant_id`,`key`),
  KEY `ix_settings_tenant_id` (`tenant_id`),
  CONSTRAINT `settings_ibfk_1` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `work_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `lawyer_id` int NOT NULL,
  `case_id` int NOT NULL,
  `date` date NOT NULL,
  `hours` decimal(6,2) NOT NULL,
  `description` varchar(1000) DEFAULT NULL,
  `source` enum('MANUAL','EXCEL_IMPORT') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lawyer_id` (`lawyer_id`),
  KEY `ix_work_logs_case_id` (`case_id`),
  KEY `ix_work_logs_tenant_id` (`tenant_id`),
  CONSTRAINT `work_logs_ibfk_1` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`),
  CONSTRAINT `work_logs_ibfk_2` FOREIGN KEY (`lawyer_id`) REFERENCES `memberships` (`id`),
  CONSTRAINT `work_logs_ibfk_3` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `narratives` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `case_id` int NOT NULL,
  `generated_text` text NOT NULL,
  `total_hours` decimal(8,2) NOT NULL,
  `total_fee` decimal(10,2) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_narratives_case_id` (`case_id`),
  KEY `ix_narratives_tenant_id` (`tenant_id`),
  CONSTRAINT `narratives_ibfk_1` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`),
  CONSTRAINT `narratives_ibfk_2` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `audit_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenant_id` int NOT NULL,
  `user_id` int NOT NULL,
  `action` varchar(100) NOT NULL,
  `target` varchar(255) NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_audit_logs_tenant_id` (`tenant_id`),
  CONSTRAINT `audit_logs_ibfk_1` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`),
  CONSTRAINT `audit_logs_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `memberships` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
