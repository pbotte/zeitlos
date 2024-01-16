-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 192.168.178.179
-- Erstellungszeit: 27. Jul 2022 um 12:53
-- Server-Version: 10.3.27-MariaDB-0+deb10u1
-- PHP-Version: 8.0.21

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

--
-- Datenbank: `zeitlos`
--

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `Products`
--

CREATE TABLE `Products` (
  `ProductID` int(11) NOT NULL,
  `ProductName` varchar(50) DEFAULT NULL,
  `ProductDescription` text DEFAULT NULL,
  `PicturePath` text DEFAULT NULL,
  `PricePerUnit` double NOT NULL DEFAULT 0,
  `kgPerUnit` double NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Daten für Tabelle `Products`
--

INSERT INTO `Products` (`ProductID`, `ProductName`, `ProductDescription`, `PicturePath`, `PricePerUnit`, `kgPerUnit`) VALUES
(1, 'Mehl', 'aus Ingelheim', NULL, 1.49, 1),
(2, 'Äpfel', 'aus eigener Ernte', NULL, 2.4, 1),
(3, 'Aprikosen', 'aus eigener Ernte', NULL, 3.2, 1);

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `Products_Scales`
--

CREATE TABLE `Products_Scales` (
  `ProductID` int(11) DEFAULT NULL,
  `ShelfName` varchar(50) NOT NULL,
  `ScaleHexStr` varchar(4) DEFAULT NULL,
  `CreatedTimestamp` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Daten für Tabelle `Products_Scales`
--

INSERT INTO `Products_Scales` (`ProductID`, `ShelfName`, `ScaleHexStr`, `CreatedTimestamp`) VALUES
(1, 'shelf01', 'b963', '2022-07-27 11:42:11');

--
-- Indizes der exportierten Tabellen
--

--
-- Indizes für die Tabelle `Products`
--
ALTER TABLE `Products`
  ADD PRIMARY KEY (`ProductID`);

--
-- Indizes für die Tabelle `Products_Scales`
--
ALTER TABLE `Products_Scales`
  ADD UNIQUE KEY `MyIndex` (`ProductID`,`ScaleHexStr`,`ShelfName`) USING BTREE;

--
-- AUTO_INCREMENT für exportierte Tabellen
--

--
-- AUTO_INCREMENT für Tabelle `Products`
--
ALTER TABLE `Products`
  MODIFY `ProductID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;
COMMIT;
