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

CREATE TABLE IF NOT EXISTS "suggestion" (
	"id" SERIAL PRIMARY KEY,
	"authorId" VARCHAR(50) NOT NULL,
	"authorUsername" VARCHAR(30) NOT NULL,
	"title" TEXT NOT NULL,
	"body" TEXT NOT NULL,
	"status" TEXT NOT NULL DEFAULT 'visible',
	"createdAt" TIMESTAMP NOT NULL,
	"editedAt" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "suggestion_vote" (
	"suggestionId" INTEGER NOT NULL,
	"userId" VARCHAR(50) NOT NULL,
	"value" INTEGER NOT NULL,
	PRIMARY KEY ("suggestionId", "userId")
);

CREATE TABLE IF NOT EXISTS "comment" (
	"id" SERIAL PRIMARY KEY,
	"suggestionId" INTEGER NOT NULL,
	"authorId" VARCHAR(50) NOT NULL,
	"authorUsername" VARCHAR(30) NOT NULL,
	"body" TEXT NOT NULL,
	"status" TEXT NOT NULL DEFAULT 'visible',
	"parentCommentId" INTEGER,
	"createdAt" TIMESTAMP NOT NULL,
	"editedAt" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "notification" (
	"id" SERIAL PRIMARY KEY,
	"userId" VARCHAR(50) NOT NULL,
	"message" TEXT NOT NULL,
	"url" TEXT,
	"read" BOOLEAN NOT NULL DEFAULT FALSE,
	"createdAt" TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "roadmap" (
	"id" SERIAL PRIMARY KEY,
	"name" TEXT NOT NULL,
	"slug" TEXT UNIQUE NOT NULL,
	"createdAt" TIMESTAMP NOT NULL,
	"updatedAt" TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "roadmap_box" (
	"id" SERIAL PRIMARY KEY,
	"roadmapId" INTEGER NOT NULL,
	"title" TEXT NOT NULL,
	"description" TEXT NOT NULL DEFAULT '',
	"status" TEXT NOT NULL DEFAULT 'planned',
	"x" INTEGER NOT NULL DEFAULT 40,
	"y" INTEGER NOT NULL DEFAULT 40
);

CREATE TABLE IF NOT EXISTS "roadmap_arrow" (
	"id" SERIAL PRIMARY KEY,
	"roadmapId" INTEGER NOT NULL,
	"fromBoxId" INTEGER NOT NULL,
	"toBoxId" INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS "roadmap_box_vote" (
	"boxId" INTEGER NOT NULL,
	"userId" VARCHAR(50) NOT NULL,
	"value" INTEGER NOT NULL,
	PRIMARY KEY ("boxId", "userId")
);

CREATE TABLE IF NOT EXISTS "roadmap_box_comment" (
	"id" SERIAL PRIMARY KEY,
	"boxId" INTEGER NOT NULL,
	"authorId" VARCHAR(50) NOT NULL,
	"authorUsername" VARCHAR(30) NOT NULL,
	"body" TEXT NOT NULL,
	"parentCommentId" INTEGER,
	"deleted" BOOLEAN NOT NULL DEFAULT FALSE,
	"createdAt" TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "roadmap_comment_vote" (
	"commentId" INTEGER NOT NULL,
	"userId" VARCHAR(50) NOT NULL,
	PRIMARY KEY ("commentId", "userId")
);

CREATE TABLE IF NOT EXISTS "organization_link" (
	"userId" VARCHAR(50) NOT NULL,
	"organizationId" TEXT NOT NULL,
	"linkedAt" TIMESTAMP NOT NULL,
	PRIMARY KEY ("userId", "organizationId")
);