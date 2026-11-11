# Changelog

## 1.4.0
- Payout runs skip merchants with a zero balance.

## 1.3.0
- handle_refund replaced handle_refund_v1, and the refund_v1 kind is no longer accepted. Refunds now post to the refunds account as well as to cash.

## 1.2.0
- Receipts moved to the billing service; format_old_receipt is no longer used here.

## 1.1.0
- handle_chargeback books the card network's fixed fee as well as the chargeback.
