# Recs API plan

1. Feature store: hourly materialization from the warehouse.
2. Model registry with numbered versions and aliases (active, previous, shadow).
3. API endpoint `/recommendations`: get features, run the model, return 20 items. Fall back to popular items if needed.
4. Model loading on the API instances, with a feature check.
5. Shadow: 10% of users, shadow queue, shadow workers, prediction log.
6. Daily comparison job.
7. Promote once the brief's criteria pass and the ML lead signs off. A/B test step TBD by Product.
8. Switch via the registry.
9. Rollback via the registry.
