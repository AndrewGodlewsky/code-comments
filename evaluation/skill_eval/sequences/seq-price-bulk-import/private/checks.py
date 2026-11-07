"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""


class Store:
    def __init__(self, log, prices):
        self.log, self.prices = log, dict(prices)

    def get(self, sku):
        self.log.append(("store.get", sku))
        return self.prices.get(sku)

    def put(self, sku, cents):
        self.log.append(("store.put", sku))
        self.prices[sku] = cents

    def put_many(self, prices):
        prices = dict(prices)
        self.log.append(("store.put_many", tuple(sorted(prices))))
        self.prices.update(prices)


class Cache:
    def __init__(self, log, entries):
        self.log, self.entries = log, dict(entries)

    def get(self, key):
        self.log.append(("cache.get", key))
        return self.entries.get(key)

    def set(self, key, value, ttl=None):
        self.log.append(("cache.set", key))
        self.entries[key] = value

    def delete(self, key):
        self.log.append(("cache.delete", key))
        self.entries.pop(key, None)

    def delete_many(self, keys):
        keys = list(keys)
        self.log.append(("cache.delete_many", tuple(sorted(keys))))
        for key in keys:
            self.entries.pop(key, None)


WRITES = ("store.put", "store.put_many", "cache.delete", "cache.delete_many", "cache.set")


def step1(module, failures):
    log = []
    store, cache = Store(log, {"sku-1": 900}), Cache(log, {"sku-1": 900, "sku-2": 50})
    expect(failures, "set_price returns previous price", lambda: module.set_price(store, cache, "sku-1", 1200), 900)
    expect(failures, "set_price updates store", lambda: store.prices.get("sku-1"), 1200)
    expect(failures, "set_price removes cache entry", lambda: "sku-1" in cache.entries, False)
    expect(failures, "set_price leaves other entries", lambda: cache.entries.get("sku-2"), 50)
    if ("store.put", "sku-1") in log and ("cache.delete", "sku-1") in log:
        expect(failures, "set_price writes store before cache delete",
               lambda: log.index(("store.put", "sku-1")) < log.index(("cache.delete", "sku-1")), True)
    for bad in (0, -5, 12.5, True, "100"):
        log3 = []
        store3, cache3 = Store(log3, {"sku-1": 900}), Cache(log3, {"sku-1": 900})
        expect_raises(failures, f"set_price invalid {bad!r}", lambda b=bad: module.set_price(store3, cache3, "sku-1", b), module.PriceError)
        expect(failures, f"set_price invalid {bad!r} touches nothing", lambda l=log3: [e for e in l if e[0] in WRITES], [])


def check():
    failures = []
    module = load("pricing", failures)
    if module is None:
        return failures
    step1(module, failures)
    if not hasattr(module, "set_prices"):
        return failures + ["set_prices is missing"]

    log = []
    store = Store(log, {"sku-1": 900, "sku-2": 400})
    cache = Cache(log, {"sku-1": 900, "sku-2": 400, "sku-7": 70})
    batch = {"sku-1": 1000, "sku-2": 450, "sku-3": 99}
    expect(failures, "set_prices returns prior prices", lambda: module.set_prices(store, cache, batch),
           {"sku-1": 900, "sku-2": 400, "sku-3": None})
    expect(failures, "store holds the new prices", lambda: store.prices, {"sku-1": 1000, "sku-2": 450, "sku-3": 99})
    expect(failures, "batched cache entries removed", lambda: sorted(cache.entries), ["sku-7"])
    puts = [e for e in log if e[0] == "store.put_many"]
    deletes = [e for e in log if e[0] == "cache.delete_many"]
    expect(failures, "one put_many with every SKU", lambda: puts, [("store.put_many", ("sku-1", "sku-2", "sku-3"))])
    expect(failures, "one delete_many with every SKU", lambda: deletes, [("cache.delete_many", ("sku-1", "sku-2", "sku-3"))])
    expect(failures, "no per-SKU writes or write-through", lambda: [e for e in log if e[0] in ("store.put", "cache.delete", "cache.set")], [])
    if puts and deletes:
        expect(failures, "store batch written before the cache batch is invalidated",
               lambda: log.index(puts[0]) < log.index(deletes[0]), True)

    for bad in (0, -5, 12.5, True, "100"):
        log2 = []
        store2 = Store(log2, {"sku-1": 900})
        cache2 = Cache(log2, {"sku-1": 900, "sku-2": 400})
        expect_raises(failures, f"set_prices rejects {bad!r}",
                      lambda b=bad: module.set_prices(store2, cache2, {"sku-1": 1000, "sku-2": b}), module.PriceError)
        expect(failures, f"set_prices with {bad!r} touches nothing", lambda l=log2: [e for e in l if e[0] in WRITES], [])
        expect(failures, f"set_prices with {bad!r} leaves the store", lambda s=store2: s.prices, {"sku-1": 900})
    return failures
