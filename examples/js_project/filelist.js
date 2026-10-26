"use strict";

// This module lists the files that match a glob pattern. It was written against
// glob 7, whose default export is a callable, callback-style function:
//
//     const glob = require("glob");
//     glob(pattern, (err, files) => ...);
//
// glob 9 removed that callable default export (it is now an object with named
// `glob` / `globSync` members that return promises), so this code breaks on the
// security upgrade. LiveFix repairs it to the current API.
const glob = require("glob");

function listMatches(pattern) {
  return new Promise((resolve, reject) => {
    glob(pattern, (err, files) => (err ? reject(err) : resolve(files)));
  });
}

module.exports = { listMatches };
