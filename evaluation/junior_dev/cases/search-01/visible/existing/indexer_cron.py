# Runs every 15 minutes from cron. To be replaced.
import psycopg
import search_client

INDEX = "products_v3"   # written directly, not through the alias

def run(last_run_at):
    with psycopg.connect("postgresql://catalog-primary/catalog") as db:
        rows = db.execute(
            "SELECT id, sku, title, description, price_cents, status "
            "FROM products WHERE updated_at > %s", (last_run_at,))
        actions = []
        for r in rows:
            if r.status == "active":
                actions.append({"index": {"_index": INDEX, "_id": r.id},
                                "doc": to_doc(r)})
            else:
                actions.append({"delete": {"_index": INDEX, "_id": r.id}})
        search_client.bulk(actions)  # any error fails the run; next run retries

    # Known gaps:
    #  - hard-deleted rows never leave the index
    #  - two runs can overlap, and the slower one can write older data last
    #  - changes take up to 15 minutes to appear

def to_doc(r):
    return {"sku": r.sku, "title": r.title,
            "description": r.description, "price": r.price_cents / 100}
