CREATE TABLE variable (
    ID_Variable INT NOT NULL AUTO_INCREMENT,
    Nom VARCHAR(100) COLLATE utf8mb4_general_ci NOT NULL,
    Indicateurs VARCHAR(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
    Unite VARCHAR(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
    PRIMARY KEY (ID_Variable),
    UNIQUE KEY Indicateurs (Indicateurs)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE localisation (
    ID_Localisation INT NOT NULL AUTO_INCREMENT,
    Latitude FLOAT(10,6) NOT NULL,
    Longitude FLOAT(10,6) NOT NULL,
    PRIMARY KEY (ID_Localisation),
    UNIQUE KEY unique_loc (Latitude, Longitude)
) ENGINE=InnoDB AUTO_INCREMENT=20799402 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE mesure (
    ID_Mesure INT NOT NULL AUTO_INCREMENT,
    Date_Heure DATETIME NOT NULL,
    Valeur FLOAT DEFAULT NULL,
    ID_Variable INT DEFAULT NULL,
    ID_Localisation INT DEFAULT NULL,
    Jour_Opti DATE GENERATED ALWAYS AS (CAST(Date_Heure AS DATE)) STORED,
    PRIMARY KEY (ID_Mesure),
    KEY ID_Variable (ID_Variable),
    KEY ID_Localisation (ID_Localisation),
    KEY idx_covering_stats (ID_Variable, Date_Heure, Valeur),
    KEY idx_turbo_graph (ID_Variable, Jour_Opti, Valeur),
    CONSTRAINT mesure_ibfk_1 FOREIGN KEY (ID_Variable) REFERENCES variable (ID_Variable),
    CONSTRAINT mesure_ibfk_2 FOREIGN KEY (ID_Localisation) REFERENCES localisation (ID_Localisation)
) ENGINE=InnoDB AUTO_INCREMENT=17421440 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE utilisateur (
    ID_Utilisateur INT AUTO_INCREMENT PRIMARY KEY,
    Nom_Utilisateur VARCHAR(80) NOT NULL,
    Email VARCHAR(254) NOT NULL UNIQUE,
    Role VARCHAR(20) NOT NULL DEFAULT 'User',
    Mot_de_Passe VARCHAR(255) NOT NULL
);

CREATE TABLE historique (
    ID_Log INT AUTO_INCREMENT PRIMARY KEY,
    Action VARCHAR(80) NOT NULL,
    Table_Concernee VARCHAR(80) NOT NULL,
    Detail VARCHAR(255) NOT NULL,
    ID_Utilisateur INT NOT NULL,
    Date_Action DATETIME NOT NULL,
    FOREIGN KEY (ID_Utilisateur) REFERENCES utilisateur (ID_Utilisateur) ON DELETE CASCADE
);

CREATE TABLE favoris_perso (
    ID_Favori INT AUTO_INCREMENT PRIMARY KEY,
    ID_Utilisateur INT NOT NULL,
    Nom_Zone VARCHAR(40) NOT NULL,
    Indicateur VARCHAR(40) NOT NULL,
    Date_Debut DATE NOT NULL,
    Date_Fin DATE NOT NULL,
    UNIQUE (ID_Utilisateur, Nom_Zone, Indicateur, Date_Debut, Date_Fin),
    FOREIGN KEY (ID_Utilisateur) REFERENCES utilisateur (ID_Utilisateur) ON DELETE CASCADE
);

CREATE TABLE avis (
    ID_Avis INT AUTO_INCREMENT PRIMARY KEY,
    ID_Utilisateur INT NOT NULL,
    Note INT NOT NULL,
    Message TEXT NOT NULL,
    Date_Avis DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Utilisateur) REFERENCES utilisateur (ID_Utilisateur) ON DELETE CASCADE
);
