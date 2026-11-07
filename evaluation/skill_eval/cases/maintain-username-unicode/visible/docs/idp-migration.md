# Identity provider migration: completed

The LDAP directory was decommissioned on 2026-09-30. User ids now live only in
the new identity provider (IdP); nothing reads or writes LDAP any more.

## IdP user id rules

- Stored as UTF-8. Letters and digits from any script, plus underscore.
- 3 to 20 characters, counted after normalization.
- The IdP treats two uids as the same account when they are equal after NFKC
  normalization and case folding. For example `ｊｏｓé` (fullwidth letters),
  `jose` followed by a combining acute accent, and `José` are one account.
- Sign-up must store the normalized form so our users table agrees with the
  IdP. Otherwise one person can end up with two rows that the IdP considers
  the same login.
