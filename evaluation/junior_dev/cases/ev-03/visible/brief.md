## Chat message fan-out: online delivery and offline storage

We're adding real-time delivery to chat. Right now clients only see new messages when they reload conversation history. I need a design that covers everything from the moment a sender presses send until every recipient has the message, whether or not they are connected at that moment.

**Fixed requirements**

- Each client holds a WebSocket to one of several gateway nodes and sends a heartbeat every 10 seconds. A user counts as offline once 30 seconds pass with no heartbeat. Assume one device per user for this version.
- A conversation has at most 200 members. The sender is not a recipient of their own message.
- Every message is written durably to the existing Message Store (the conversation history database), which gives it a per-conversation sequence number. Acknowledge the sender only after that write commits. The ack carries the message id and the sequence number. If the write fails, the sender gets an error and no one receives anything. The client then retries with the same client-generated message id, and a retry must never create a second copy.
- Fan-out must not run on the sender's request path, and the sender's ack must not wait for any recipient. Once a message has been acknowledged it must eventually reach every recipient, even if a process crashes right after the write.
- An online recipient's client acknowledges each message it receives. If that ack does not arrive within 5 seconds, treat the recipient as offline for that message.
- For offline recipients, keep what they have missed until they reconnect, for up to 30 days, and send a mobile push notification. Push is best effort: it is never retried, and a failed push must never affect what is stored.
- On reconnect, the client must receive everything it missed, in sequence-number order within each conversation.
- Delivery may be at-least-once. Clients drop duplicates by message id.

Out of scope: typing indicators, read receipts, edits and deletes.

**What I want back**

An ASCII diagram in a fenced code block that shows the components and the numbered flow (send, fan-out, reconnect). Follow it with short notes that say where each piece of state lives and what happens on each failure.
