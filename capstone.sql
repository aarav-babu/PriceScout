-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Nov 08, 2023 at 12:36 PM
-- Server version: 10.4.28-MariaDB
-- PHP Version: 8.0.28

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `capstone`
--

-- --------------------------------------------------------

--
-- Table structure for table `laptops`
--

CREATE TABLE `laptops` (
  `post_id` int(11) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `brandlap` varchar(255) DEFAULT NULL,
  `model` varchar(255) DEFAULT NULL,
  `processor` varchar(255) DEFAULT NULL,
  `ram_size` float DEFAULT NULL,
  `memory_type` varchar(255) DEFAULT NULL,
  `memory_size` float DEFAULT NULL,
  `display_size` float DEFAULT NULL,
  `refresh_rate` int(11) DEFAULT NULL,
  `battery` int(11) DEFAULT NULL,
  `laptop_type` varchar(255) DEFAULT NULL,
  `description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `mobiles`
--

CREATE TABLE `mobiles` (
  `post_id` int(11) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `brand` varchar(255) DEFAULT NULL,
  `model_name` varchar(255) DEFAULT NULL,
  `sim_slots` int(11) DEFAULT NULL,
  `processor` varchar(255) DEFAULT NULL,
  `ram` int(11) DEFAULT NULL,
  `storage_size` int(11) DEFAULT NULL,
  `battery_size` int(11) DEFAULT NULL,
  `display` varchar(255) DEFAULT NULL,
  `camera` varchar(255) DEFAULT NULL,
  `description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `price`
--

CREATE TABLE `price` (
  `email` varchar(255) DEFAULT NULL,
  `post_id` int(11) DEFAULT NULL,
  `post_type` varchar(255) DEFAULT NULL,
  `brand` varchar(255) DEFAULT NULL,
  `model` varchar(255) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `price` float DEFAULT NULL,
  `pricing_status` varchar(16) NOT NULL DEFAULT 'pending',
  `price_source` varchar(64) DEFAULT NULL,
  `price_confidence` double DEFAULT NULL,
  `priced_at` datetime DEFAULT NULL,
  `model_version` char(36) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `username` varchar(255) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `number` varchar(255) NOT NULL,
  `password` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `vehicle`
--

CREATE TABLE `vehicle` (
  `post_id` int(11) NOT NULL,
  `user_email` varchar(255) DEFAULT NULL,
  `brand` varchar(255) DEFAULT NULL,
  `name_model` varchar(255) DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `vehicle_type` varchar(50) DEFAULT NULL,
  `model_year` int(11) DEFAULT NULL,
  `color` varchar(50) DEFAULT NULL,
  `km_driven` int(11) DEFAULT NULL,
  `mileage` int(11) DEFAULT NULL,
  `fuel_type` varchar(50) DEFAULT NULL,
  `transmission` varchar(50) DEFAULT NULL,
  `owner_type` varchar(50) DEFAULT NULL,
  `engine_capacity` varchar(50) DEFAULT NULL,
  `power` varchar(50) DEFAULT NULL,
  `seats` int(11) DEFAULT NULL,
  `description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
--
-- Hosted pricing pipeline
--

CREATE TABLE `market_queries` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `category` varchar(32) NOT NULL,
  `brand` varchar(255) NOT NULL,
  `model` varchar(255) NOT NULL,
  `query_text` varchar(512) NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `refresh_minutes` int NOT NULL,
  `volatility` double NOT NULL DEFAULT 0,
  `last_collected_at` datetime DEFAULT NULL,
  `next_collection_at` datetime NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `market_query_item` (`category`,`brand`,`model`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `pipeline_runs` (
  `id` char(36) NOT NULL,
  `job_type` varchar(32) NOT NULL,
  `status` varchar(16) NOT NULL,
  `details` text DEFAULT NULL,
  `started_at` datetime NOT NULL,
  `finished_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `pipeline_run_started` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `market_observations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `query_id` bigint NOT NULL,
  `collection_id` char(36) NOT NULL,
  `provider` varchar(64) NOT NULL,
  `external_id` varchar(255) NOT NULL,
  `title` text NOT NULL,
  `item_condition` varchar(128) DEFAULT NULL,
  `price` decimal(14,2) NOT NULL,
  `currency` char(3) NOT NULL,
  `listing_url` text DEFAULT NULL,
  `observed_at` datetime NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `observations_query_time` (`query_id`,`observed_at`),
  KEY `observations_expiry` (`expires_at`),
  CONSTRAINT `observations_query_fk` FOREIGN KEY (`query_id`)
    REFERENCES `market_queries` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `model_versions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version` char(36) NOT NULL,
  `target_currency` char(3) NOT NULL,
  `row_count` int NOT NULL,
  `median_absolute_percentage_error` double DEFAULT NULL,
  `artifact` longblob NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 0,
  `trained_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `model_version` (`version`),
  KEY `active_model` (`active`,`trained_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `laptops`
--
ALTER TABLE `laptops`
  ADD PRIMARY KEY (`post_id`),
  ADD KEY `email` (`email`);

--
-- Indexes for table `mobiles`
--
ALTER TABLE `mobiles`
  ADD PRIMARY KEY (`post_id`),
  ADD KEY `email` (`email`);

--
-- Indexes for table `price`
--
ALTER TABLE `price`
  ADD KEY `email` (`email`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`email`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `number` (`number`);

--
-- Indexes for table `vehicle`
--
ALTER TABLE `vehicle`
  ADD PRIMARY KEY (`post_id`),
  ADD KEY `user_email` (`user_email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `laptops`
--
ALTER TABLE `laptops`
  MODIFY `post_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `mobiles`
--
ALTER TABLE `mobiles`
  MODIFY `post_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vehicle`
--
ALTER TABLE `vehicle`
  MODIFY `post_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `laptops`
--
ALTER TABLE `laptops`
  ADD CONSTRAINT `laptops_ibfk_1` FOREIGN KEY (`email`) REFERENCES `users` (`email`) ON DELETE CASCADE;

--
-- Constraints for table `mobiles`
--
ALTER TABLE `mobiles`
  ADD CONSTRAINT `mobiles_ibfk_1` FOREIGN KEY (`email`) REFERENCES `users` (`email`) ON DELETE CASCADE;

--
-- Constraints for table `price`
--
ALTER TABLE `price`
  ADD CONSTRAINT `price_ibfk_1` FOREIGN KEY (`email`) REFERENCES `users` (`email`);

--
-- Constraints for table `vehicle`
--
ALTER TABLE `vehicle`
  ADD CONSTRAINT `vehicle_ibfk_1` FOREIGN KEY (`user_email`) REFERENCES `users` (`email`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
