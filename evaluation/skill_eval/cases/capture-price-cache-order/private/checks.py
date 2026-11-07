"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


class Store:
    def __init__(self, log, prices):
        self.log, self.prices = log, dict(prices)

    def get(self, sku):
        self.log.append(("store.get", sku))
        return self.prices.get(sku)

    def put(self, sku, cents):
        self.log.append(("store.put", sku))
        self.prices[sku] = cents


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


def check():
    failures = []
    module = load("pricing", failures)
    if module is None:
        return failures
    log = []
    store, cache = Store(log, {"sku-1": 900}), Cache(log, {"sku-1": 900, "sku-2": 50})
    expect(failures, "returns previous price", lambda: module.set_price(store, cache, "sku-1", 1200), 900)
    expect(failures, "store updated", lambda: store.prices.get("sku-1"), 1200)
    expect(failures, "cache entry removed", lambda: "sku-1" in cache.entries, False)
    expect(failures, "other cache entries untouched", lambda: cache.entries.get("sku-2"), 50)
    expect(failures, "cache deleted exactly once", lambda: log.count(("cache.delete", "sku-1")), 1)
    expect(failures, "no write-through set", lambda: [e for e in log if e[0] == "cache.set"], [])
    if ("store.put", "sku-1") in log and ("cache.delete", "sku-1") in log:
        expect(failures, "store written before cache delete",
               lambda: log.index(("store.put", "sku-1")) < log.index(("cache.delete", "sku-1")), True)

    log2 = []
    store2, cache2 = Store(log2, {}), Cache(log2, {})
    expect(failures, "new sku returns None", lambda: module.set_price(store2, cache2, "sku-9", 300), None)
    expect(failures, "uncached sku still invalidated", lambda: ("cache.delete", "sku-9") in log2, True)

    for bad in (0, -5, 12.5, True, "100"):
        log3 = []
        store3, cache3 = Store(log3, {"sku-1": 900}), Cache(log3, {"sku-1": 900})
        expect_raises(failures, f"invalid price {bad!r}", lambda b=bad: module.set_price(store3, cache3, "sku-1", b), module.PriceError if hasattr(module, "PriceError") else ValueError)
        expect(failures, f"invalid price {bad!r} touches nothing",
               lambda l=log3: [e for e in l if e[0] in ("store.put", "cache.delete", "cache.set")], [])
    return failures
