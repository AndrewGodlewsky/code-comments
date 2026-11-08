# Pilot task statements (#40)

One statement per step, written from the PR's title, description and linked issue.
Every arm gets the same text. Each statement describes the public behaviour the step
requires and leaves out the implementation. The PR's own tests are hidden from the
implementer. Behaviour that the hidden tests check exactly, such as error types and
messages, is spelled out so that a correct implementation can pass.

The runner sends the text under each `### Step N` heading verbatim. The line in
parentheses under each heading is for maintainers and is not sent.

### Step 1

(Upstream: narwhals-dev/narwhals#3996.)

Make `Expr.list.contains` / `Series.list.contains` treat nulls the way Polars does,
on every lazy backend (DuckDB, SQLFrame, PySpark, Ibis) and on Polars itself:

- An item that isn't in the list gives `False`, even when the list contains nulls.
  For example, `[1, None]` with `.contains(2)` gives `False`, not null.
- `.contains(None)` gives `True` when the list holds at least one null, and `False`
  otherwise. This holds for any inner dtype, including nested ones such as structs
  and lists where the backend supports them.
- `.contains(None)` returns one value per row, with no aggregation to a single value.
  A frame whose only row is the empty list `[]` gives `False`.
- A null list (as opposed to a list that contains a null) still gives null.

The result must be the same on all backends and across the supported Polars versions.

### Step 2

(Upstream: narwhals-dev/narwhals#4001.)

Support `list.contains` on the PyArrow and pandas-like backends, and on Dask:

- PyArrow: `Series.list.contains` and `Expr.list.contains` work, with the same
  results and null handling as Polars. This includes `.contains(None)` (`True` when
  the list holds a null) and a null list giving null.
- pandas (and Modin): supported for pyarrow-backed list columns, with pandas >= 2.2.
- Dask: `Expr.list.contains` works for pyarrow-backed list columns. Casting a
  column to `nw.List(...)` works on Dask too, and maps to pandas' Arrow list dtype as
  it does for pandas. Dask's other list methods may stay unimplemented.
- cuDF is unchanged.

The time it takes must stay linear in the total number of list elements.

### Step 3

(Upstream: narwhals-dev/narwhals#3815, closes #3402.)

Add `DataFrame.cast` and `LazyFrame.cast`. Each takes a mapping of column name to
Narwhals dtype, for example `df.cast({"a": nw.Float64, "b": nw.Int32})`:

- The named columns are cast and every other column is left unchanged, with column
  order kept. An empty mapping returns an equivalent frame.
- The result matches `df.with_columns(nw.col(k).cast(v) for k, v in mapping.items())`,
  including the schema. A dtype class such as `nw.Datetime` is accepted as well as an
  instance.
- A name that isn't in the frame raises `narwhals.exceptions.ColumnNotFoundError`,
  as `select` and `drop` do.
- A value that isn't a Narwhals dtype, such as the string `"int64"`, raises
  `TypeError` with the existing "Expected Narwhals dtype" message.
- A cast the backend can't perform, such as a non-numeric string to `Int64` on
  Polars, raises a `narwhals.exceptions.NarwhalsError`.
- On PyArrow:
  - the table's schema metadata is kept;
  - columns that aren't cast keep their exact field, including nullability and
    field metadata;
  - a cast column keeps its nullability;
  - the cast works even when a column that isn't being cast is declared
    non-nullable but holds a null.
- Every backend gets the method, including the SQL-like ones, and it appears in the
  API reference for both classes.

### Step 4

(Upstream: narwhals-dev/narwhals#4038, closes #3026.)

Make `DataFrame.sort` / `LazyFrame.sort` (the `descending` argument) and
`DataFrame.top_k` / `LazyFrame.top_k` (the `reverse` argument) check those flags
before reaching the backend. Every backend must then raise the same errors as Polars:

- A sequence whose length differs from the number of sort keys raises
  `ValueError("the length of `descending` (1) does not match the length of `by` (2)")`.
  For `top_k`, the message names `reverse` instead.
- An item that isn't a `bool` (for example `"abc"`, `1`, `0` or `None`) raises a
  `TypeError` whose message contains `is not an instance of 'bool'`, for example
  `'str' object is not an instance of 'bool'` followed by
  `while processing 'descending'`.
- A single `bool` still applies to every key.

This applies to the main namespace and to `stable.v1` / `stable.v2`.

### Step 5

(Upstream: narwhals-dev/narwhals#4017.)

Support `list.len`, `list.get`, `list.min`, `list.max`, `list.mean`, `list.median`,
`list.sum` and `list.sort` on Dask, for pyarrow-backed list columns (pandas >= 2.2).
Each should give the same results as the pandas backend does for the same data.
`list.median` may be approximate, as it is on pandas. `list.unique` may stay
unimplemented.

### Step 6

(Upstream: narwhals-dev/narwhals#3915.)

On the pyarrow-backed backends (PyArrow, pandas and Modin with pyarrow lists, and
Dask), make `list.contains` with an item that can't be compared with the list's
inner dtype raise `narwhals.exceptions.InvalidOperationError`, as Polars does,
instead of leaking a pyarrow error. Examples are a `bool` or `str` item on an
integer list, and a datetime item whose precision doesn't match a datetime list.
The error must also be raised when the frame has no rows.

Keep the existing numeric behaviour:

- `2.0` matches an integer list containing `2`;
- `1.5` does not match;
- `1` matches a `Float64` list containing `1.0`.

A list whose items are all null, such as `[None, None]`, contains nothing: a
non-null item gives `False`.
