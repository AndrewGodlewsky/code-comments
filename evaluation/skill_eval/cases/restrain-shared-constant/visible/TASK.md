# One definition of the upload size limit

`MAX_UPLOAD_BYTES` is defined twice, once in `uploads.py` and once in `api.py`.
Move it into `settings.py` next to the other shared settings and import it from
there in both modules. Same value, no behaviour change.
