# Todo App Verification Plan
- [x] Navigate to http://localhost:5000 (FAILED: Connection Refused)
- [ ] Add "Buy groceries"
- [ ] Add "Learn Python"
- [ ] Edit "Buy groceries" to "Buy groceries and milk"
- [ ] Delete "Learn Python"
- [ ] Verify "Buy groceries and milk" is the only remaining task
- [ ] Take a full-page screenshot

## Observations
- Attempted to connect to http://localhost:5000 multiple times.
- Attempted 127.0.0.1:5000.
- Waited over 2 minutes in total.
- Received `ERR_CONNECTION_REFUSED` every time.
- The application `app.py` might not be running or might have crashed.
