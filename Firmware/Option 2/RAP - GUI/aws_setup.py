import os

def main():
    print("=== AWS Credential Setup ===")
    access_key = input("Enter your IAM User Access Key ID: ").strip()
    secret_key = input("Enter your IAM User Secret Access Key: ").strip()
    region = input("Enter your default AWS region (e.g., ap-southeast-2): ").strip()

    # AWS config directory
    aws_dir = os.path.expanduser("~/.aws")
    os.makedirs(aws_dir, exist_ok=True)

    # Write credentials file
    cred_path = os.path.join(aws_dir, "credentials")
    with open(cred_path, "w") as f:
        f.write("[default]\n")
        f.write(f"aws_access_key_id = {access_key}\n")
        f.write(f"aws_secret_access_key = {secret_key}\n")

    # Write config file
    config_path = os.path.join(aws_dir, "config")
    with open(config_path, "w") as f:
        f.write("[default]\n")
        f.write(f"region = {region}\n")
        f.write("output = json\n")

    print(f"\n✅ Credentials saved to {cred_path}")
    print(f"✅ Config saved to {config_path}")
    print("You can now run your db_pull.exe without hardcoding keys.")

if __name__ == "__main__":
    main()