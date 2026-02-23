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

CREATE DATABASE IF NOT EXISTS `capstone`;
USE `capstone`;

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
  `price` float DEFAULT NULL
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

-- --------------------------------------------------------
-- Query-pattern indexes
-- --------------------------------------------------------

ALTER TABLE `vehicle`
  ADD INDEX `idx_vehicle_brand` (`brand`),
  ADD INDEX `idx_vehicle_location` (`location`),
  ADD INDEX `idx_vehicle_model_year` (`model_year`);

ALTER TABLE `mobiles`
  ADD INDEX `idx_mobiles_brand` (`brand`);

ALTER TABLE `laptops`
  ADD INDEX `idx_laptops_brandlap` (`brandlap`);

ALTER TABLE `price`
  ADD INDEX `idx_price_post_type` (`post_type`),
  ADD INDEX `idx_price_brand` (`brand`),
  ADD INDEX `idx_price_email_post_type` (`email`, `post_type`);

-- --------------------------------------------------------
-- Unique constraints for dedupe (idempotent upserts)
-- --------------------------------------------------------

ALTER TABLE `vehicle`
  ADD UNIQUE KEY `uq_vehicle_listing` (`user_email`(100), `brand`(50), `name_model`(100), `model_year`, `km_driven`);

ALTER TABLE `mobiles`
  ADD UNIQUE KEY `uq_mobile_listing` (`email`(100), `brand`(50), `model_name`(100), `storage_size`, `ram`);

ALTER TABLE `laptops`
  ADD UNIQUE KEY `uq_laptop_listing` (`email`(100), `brandlap`(50), `model`(100), `processor`(100), `ram_size`);

-- --------------------------------------------------------
-- Ingestion log table
-- --------------------------------------------------------

CREATE TABLE `ingestion_log` (
  `run_id` int(11) NOT NULL AUTO_INCREMENT,
  `run_type` varchar(50) NOT NULL COMMENT 'scrape | form_vehicle | form_mobile | form_laptop',
  `started_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at` datetime DEFAULT NULL,
  `listings_processed` int(11) NOT NULL DEFAULT 0,
  `listings_inserted` int(11) NOT NULL DEFAULT 0,
  `listings_deduped` int(11) NOT NULL DEFAULT 0,
  `errors` int(11) NOT NULL DEFAULT 0,
  `duration_seconds` float DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'running' COMMENT 'running | success | failed',
  `error_detail` text DEFAULT NULL,
  PRIMARY KEY (`run_id`),
  INDEX `idx_ingestion_started` (`started_at`),
  INDEX `idx_ingestion_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
