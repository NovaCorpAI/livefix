# Example: a JavaScript / npm project (LiveFix is not Python-specific)

This example proves the LiveFix repair loop generalizes past Python to a second
ecosystem. It is a tiny npm package whose security upgrade removes the API it
uses, exactly like the Pillow example, but in JavaScript and verified with
Node's own test runner (`node --test`).

## The break (real, not invented)

`filelist.js` was written against **glob 7**, whose default export is a
callable, callback-style function:

```js
const glob = require("glob");
glob(pattern, (err, files) => ...);
```

**glob 9 removed that callable default export.** It is now an object with named
`glob` / `globSync` members, so the old code throws
`TypeError: glob is not a function` the moment the dependency is upgraded. You
can see the change yourself by installing `glob@7` and then `glob@10` and
calling `require("glob")`.

So upgrading glob for a security fix turns the build red, the same two-wall
problem the Python example shows: the safe version is known only from the live
web, and the upgrade breaks the code.

## What LiveFix does here

Run the repair loop against this project with `node --test` as the test command.
LiveFix reads the failing stack trace, locates `filelist.js` (never the test
file, which it treats as read-only), and has the model rewrite it to the current
glob API, looping until `node --test` is green. The test file is the spec: the
agent is not allowed to make the test pass by editing the test.

```bash
cd examples/js_project
npm install glob@10.4.5   # the security upgrade that breaks the old API
node --test               # red: TypeError: glob is not a function
python -m livefix.remediate --project . --package glob \
    --advisory <advisory-id> --manifest package.json \
    --test "node --test" --install
node --test               # green
```

The repair step is identical to the Python path: the only ecosystem-specific
pieces are reading a Node stack trace, validating the edit with `node --check`
instead of `ast.parse`, bumping `package.json` instead of `requirements.txt`,
and installing with `npm` instead of `pip`.
