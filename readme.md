# Raynbo Games Site
This is the respository for the Raynbo Games website.

## Setup

### Database
To activate the virtual enviornment run:
```./env/Scripts/Activate.ps1```
To initialize the PostgreSQL database run:
```python -m flask --app Site init-db```
To update the PostgreSQL database run:
```python -m flask --app Site update-db```
To change a users auth level via the console:
```python -m flask --app Site set-user-auth --username USER_NAME --auth AUTH_LEVEL```

python -m flask --app Site set-user-auth --username TestUser2 --auth 1