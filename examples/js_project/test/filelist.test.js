"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { listMatches } = require("../filelist.js");

test("listMatches returns the matching files as an array", async () => {
  const files = await listMatches("*.json");
  assert.ok(Array.isArray(files), "expected an array of paths");
  assert.ok(
    files.includes("package.json"),
    "expected package.json among the matches"
  );
});
