I added `--limit N` to the `tasks` command. It prints at most the first N tasks that it would otherwise show, after the `--all` filter and in file order. Without `--limit`, the output is unchanged.

Changes are in `tasks/cli.py`:
- `build_parser()` registers `--limit` as an integer option.
- `main()` slices the visible list when `--limit` is given. A negative value is rejected with a usage error (exit code 2). `visible()` is untouched.

Manual checks against a sample file with tasks a (open), b (done), c (open), d (open):
- no flag: a, c, d
- `--all`: a, b, c, d
- `--limit 0`: no output
- `--limit 1`: a
- `--limit 2`: a, c
- `--limit 10`: a, c, d
- `--all --limit 2`: a, b
- `--limit -1`: usage error

The package has no test suite, so these checks were run by hand and no test file was added. The changes are uncommitted, and I did not use git or task tracking. I did not reference an issue number in the code because I had no way to verify it from here.
