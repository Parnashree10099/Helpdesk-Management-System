from pwdlib import PasswordHash

# Create our password hashing tool
password_hash = PasswordHash.recommended()


# Convert a plain password into a secure hash
def hash_password(password: str) -> str:
    return password_hash.hash(password)


# Check whether a password matches its stored hash
def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)