# API v3 naming decision

**Decision (API guild):** Fields that hold human-readable labels use the
`display_` prefix. For profiles, `name` becomes `display_name`.

## Thread

**Marta (mobile, Android):** Android app 4.x reads `name` from the profile
response and crashes when the key is missing. We cannot change shipped 4.x
builds. Please keep sending `name`, with the same value as `display_name`, until
4.x is out of support. We are raising the minimum supported Android version to
5.0 with a forced upgrade on 2027-02-01; after that, `name` can go.

**Leo (web):** Does iOS need the old key too? I thought the iOS app still reads
`name` as well.

**Marta:** No. iOS switched to `display_name` in 6.2 and every supported iOS
build is newer than that. Only Android 4.x needs `name`.

**Leo (web):** Web already reads `display_name`. Fine by us.
