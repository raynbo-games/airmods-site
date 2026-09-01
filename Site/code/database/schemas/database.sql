CREATE TABLE IF NOT EXISTS "game" (
	"id" TEXT PRIMARY KEY UNIQUE,
	"slug" TEXT,
	"slugProperCase" TEXT,
	"name" TEXT NOT NULL,
	"description" TEXT NOT NULL,
	"iconImageId" TEXT,
	"organizationId" TEXT NOT NULL,
	"createdAt" TIMESTAMP NOT NULL,
	"visibility" TEXT NOT NULL,
	"lastVersionUpdate" TIMESTAMP NOT NULL,
	"archivedAt" TIMESTAMP,
	"loadingScreenImageId" TEXT,
	"logoImageId" TEXT,
	"videoId" TEXT,
	"links" JSONB NOT NULL,
	"plays" INTEGER NOT NULL,
	"favorites" INTEGER NOT NULL,
	"plays24h" INTEGER NOT NULL,
	"uniquePlays24h" INTEGER NOT NULL,
	"platforms" JSONB NOT NULL,
	"liveStats" JSONB NOT NULL,
	"gameStats" JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS "organization" (
	"id" TEXT PRIMARY KEY UNIQUE,
	"slug" TEXT NOT NULL,
	"slugProperCase" TEXT NOT NULL,
	"name" TEXT NOT NULL,
	"description" TEXT NOT NULL,
	"iconImageId" TEXT NOT NULL,
	"createdAt" TIMESTAMP NOT NULL,
	"adminBanned" BOOLEAN NOT NULL,
	"orgStats" JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS "json" (
	"id" TEXT PRIMARY KEY UNIQUE,
	"data" JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS "user" (
    "id" VARCHAR(50) PRIMARY KEY UNIQUE NOT NULL,
    "email" VARCHAR(120) NOT NULL,
    "username" VARCHAR(30) UNIQUE,
	"auth" INT NOT NULL DEFAULT 0,
	"notes" TEXT
);

CREATE TABLE IF NOT EXISTS "audit_log" (
	"id" SERIAL PRIMARY KEY,
	"actorId" VARCHAR(50) NOT NULL,
	"actorUsername" VARCHAR(30) NOT NULL,
	"action" TEXT NOT NULL,
	"targetId" VARCHAR(50),
	"targetUsername" VARCHAR(30),
	"details" TEXT,
	"reason" TEXT NOT NULL,
	"createdAt" TIMESTAMP NOT NULL
);