DROP TABLE IF EXISTS "game";
DROP TABLE IF EXISTS "organization";
DROP TABLE IF EXISTS "json";

CREATE TABLE "game" (
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

CREATE TABLE "organization" (
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

CREATE TABLE "json" (
	"id" TEXT PRIMARY KEY UNIQUE,
	"data" JSONB NOT NULL
);
