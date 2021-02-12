CREATE DATABASE IF NOT EXISTS simulatorDB;
USE simulatorDB;

DROP TABLE IF EXISTS `alice_sim_DB`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `alice_sim_DB` (
  `requestIP` varchar(255) NOT NULL,
  `complete` tinyint(1) DEFAULT NULL,
  `exchangedKey` text,
  `verified` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`requestIP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `bob_sim_DB`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `bob_sim_DB` (
  `requestIP` varchar(255) NOT NULL,
  `complete` tinyint(1) DEFAULT NULL,
  `exchangedKey` text,
  `verified` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`requestIP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `aliceSim_pre_keys`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `aliceSim_pre_keys` (
  `keyID` varchar(255) NOT NULL,
  `TTL` int NOT NULL,
  PRIMARY KEY (`keyID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `bobSim_pre_keys`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `bobSim_pre_keys` (
  `keyID` varchar(255) NOT NULL,
  `TTL` int NOT NULL,
  PRIMARY KEY (`keyID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
