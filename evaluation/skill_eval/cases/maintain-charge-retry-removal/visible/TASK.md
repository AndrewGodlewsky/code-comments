# Remove the LB-311 retry

LB-311 is fixed (`docs/lb-311.md`). Remove the connection-reset retry from
`submit_charge`. A `ConnectionResetError` should now reach the caller as
`ChargeFailed`, with the original error kept as its cause, so checkout takes
its existing "payment status unknown" path.
