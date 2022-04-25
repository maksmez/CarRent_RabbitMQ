--
-- Файл сгенерирован с помощью SQLiteStudio v3.3.3 в Пн апр 25 15:47:21 2022
--
-- Использованная кодировка текста: UTF-8
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Таблица: Cars
CREATE TABLE "Cars" (
	"Id" INTEGER NOT NULL, 
	"CompanyID" INTEGER NOT NULL, 
	"Location" VARCHAR(250) NOT NULL, 
	"Photos" VARCHAR, 
	"RentCondition" VARCHAR, 
	"Header" VARCHAR NOT NULL, 
	"Driver" BOOLEAN NOT NULL, 
	status BOOLEAN, 
	"CategoryID" INTEGER NOT NULL, 
	"CategoryVU" VARCHAR NOT NULL, 
	"DateDel" DATE, 
	"FixedRate" NUMERIC, 
	"Percent" NUMERIC, 
	"Brand_and_name" VARCHAR NOT NULL, 
	"Transmission" INTEGER, 
	"Engine" INTEGER, 
	"Car_type" INTEGER, 
	"Drive" INTEGER, 
	"Wheel_drive" INTEGER, 
	"Year" INTEGER NOT NULL, 
	"Power" INTEGER NOT NULL, 
	"Price" INTEGER NOT NULL, 
	PRIMARY KEY ("Id"), 
	FOREIGN KEY("CompanyID") REFERENCES "Company" ("Id"), 
	FOREIGN KEY("CategoryID") REFERENCES "Category" ("Id")
);

-- Таблица: Category
CREATE TABLE "Category" (
	"Id" INTEGER NOT NULL, 
	"NameCat" VARCHAR NOT NULL, 
	"Icon" VARCHAR, 
	"DateDel" DATE, 
	PRIMARY KEY ("Id")
);

-- Таблица: Company
CREATE TABLE "Company" (
	"Id" INTEGER NOT NULL, 
	"Name" VARCHAR NOT NULL, 
	"Phone" VARCHAR NOT NULL, 
	"Email" VARCHAR, 
	"Note" VARCHAR, 
	"DateDel" DATE, 
	"FIOContact" VARCHAR NOT NULL, 
	"ContactPhone" VARCHAR NOT NULL, 
	"ContactEmail" VARCHAR, 
	PRIMARY KEY ("Id")
);

-- Таблица: Contract
CREATE TABLE "Contract" (
	"Id" INTEGER NOT NULL, 
	"ClientId" INTEGER NOT NULL, 
	"CarId" INTEGER NOT NULL, 
	"DateStartContract" DATE NOT NULL, 
	"DateEndContract" DATE NOT NULL, 
	"Driver" BOOLEAN NOT NULL, 
	"Note" VARCHAR, 
	"Status" INTEGER NOT NULL, 
	"Comission" NUMERIC NOT NULL, 
	"Cost" INTEGER NOT NULL, 
	"DateDel" DATE, 
	PRIMARY KEY ("Id"), 
	FOREIGN KEY("ClientId") REFERENCES "Person" ("Id"), 
	FOREIGN KEY("CarId") REFERENCES "Cars" ("Id")
);

-- Таблица: Favorites
CREATE TABLE "Favorites" (
	"Id" INTEGER NOT NULL, 
	"ClientId" INTEGER NOT NULL, 
	"CarId" INTEGER NOT NULL, 
	"Date_add" DATE, 
	"DateDel" DATE, 
	PRIMARY KEY ("Id"), 
	FOREIGN KEY("ClientId") REFERENCES "Person" ("Id"), 
	FOREIGN KEY("CarId") REFERENCES "Cars" ("Id")
);

-- Таблица: Person
CREATE TABLE "Person" (
	"Id" INTEGER NOT NULL, 
	"CompanyID" INTEGER, 
	"Name" VARCHAR NOT NULL, 
	"Surname" VARCHAR NOT NULL, 
	"Birthday" DATE, 
	"Phone" VARCHAR NOT NULL, 
	"Password" VARCHAR NOT NULL, 
	"Token" VARCHAR NOT NULL, 
	"Email" VARCHAR, 
	"Position" INTEGER, 
	"Comment" VARCHAR, 
	"CategoryVuID" VARCHAR NOT NULL, 
	"NumVU" VARCHAR NOT NULL, 
	"DateDel" DATE, 
	PRIMARY KEY ("Id")
);

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
